import torch
import folder_paths
import comfy.utils
import comfy.sd

class LoadBLoRA:
    BLOCKS = {
        'content': [
            'unet.up_blocks.0.attentions.0',
            'unet_up_blocks_0_attentions_0',
            ],
        'style': [
            'unet.up_blocks.0.attentions.1',
            'unet_up_blocks_0_attentions_1',
            ],
    }    
    def __init__(self):
        self.loaded_lora = None

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "model": ("MODEL",),
                              "lora_name": (folder_paths.get_filename_list("loras"), ),
                              "load_style": ("BOOLEAN", {"default": True}),
                              "load_content": ("BOOLEAN", {"default": False}),
                              "strength": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                              }}
    RETURN_TYPES = ("MODEL",)
    FUNCTION = "main"

    CATEGORY = "loaders"

    def convert_to_kohya(self, lora_dict):
        # This is an alternative of the tools from diffusers.utils if diffusers is not up-to-date
        new_lora_dict = {}
        for key, value in lora_dict.items():
            # e.g. key='unet.up_blocks.0.attentions.1.transformer_blocks.0.attn1.to_k.lora.down.weight'
            parts = key.rsplit('.', 3)
            first_part = parts[0].replace('.', '_')
            # e.g. first_part='unet_up_blocks_0_attentions_1_transformer_blocks_0_attn1_to_k'

            last_three = '.'.join(parts[-3:])
            last_three_modified = last_three.replace('.', '_', 1)
            # e.g. last_three_modified='lora_down.weight'

            new_key = f"lora_{first_part}.{last_three_modified}"
            # e.g. new_key='lora_unet_up_blocks_0_attentions_1_transformer_blocks_0_attn1_to_k.lora_down.weight'

            new_lora_dict[new_key] = value
            if "lora_down" in new_key:
                alpha_key = f'{new_key.split(".")[0]}.alpha'
                new_lora_dict[alpha_key] = torch.tensor(len(value))

        return new_lora_dict

    def filter_lora(self, lora, load_style, load_content):
        # Initialize an empty dictionary to store the filtered items
        filtered_lora = {}

        # Combine the keys from BLOCKS based on the flags
        keys_to_include = []
        if load_style:
            keys_to_include.extend(self.BLOCKS['style'])
        if load_content:
            keys_to_include.extend(self.BLOCKS['content'])

        # Filter the items in lora
        for key, value in lora.items():
            if any(substring in key for substring in keys_to_include):
                filtered_lora[key] = value


        return filtered_lora

    def main(self, model, lora_name, load_style, load_content, strength):
        if strength == 0:
            return (model,)
        if not load_style and not load_content:
            return (model,)

        lora_path = folder_paths.get_full_path("loras", lora_name)
        lora = None
        if self.loaded_lora is not None:
            if self.loaded_lora[0] == lora_path:
                lora = self.loaded_lora[1]
            else:
                temp = self.loaded_lora
                self.loaded_lora = None
                del temp

        if lora is None:
            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            self.loaded_lora = (lora_path, lora)

        lora = self.filter_lora(lora, load_style, load_content)

        try:
            from diffusers.utils import convert_all_state_dict_to_peft, convert_state_dict_to_kohya

            def convert_to_kohya(diffusers_state_dict):
                peft_state_dict = convert_all_state_dict_to_peft(diffusers_state_dict)
                kohya_state_dict = convert_state_dict_to_kohya(peft_state_dict)
                return kohya_state_dict

            lora = convert_to_kohya(lora)
        except ImportError as e:
            print("Please upgrade your `diffusers`. For now, fall back to manually conversion.")
            lora = self.convert_to_kohya(lora)

        if len(lora)==0:
            raise Exception("not a B-Lora model")

        model_lora, _ = comfy.sd.load_lora_for_models(model, None, lora, strength, strength_clip=0)
        return (model_lora, )




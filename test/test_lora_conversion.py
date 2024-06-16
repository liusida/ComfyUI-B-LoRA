# need diffusers >= v0.29.0

from diffusers.utils import convert_all_state_dict_to_peft, convert_state_dict_to_kohya

def convert_to_kohya(diffusers_state_dict):
    peft_state_dict = convert_all_state_dict_to_peft(diffusers_state_dict)
    kohya_state_dict = convert_state_dict_to_kohya(peft_state_dict)
    return kohya_state_dict

from ..nodes.load_b_lora import LoadBLoRA

# LoadBLoRA.rename_keys should be equal to convert_to_kohya
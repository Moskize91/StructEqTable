import torch

from torch import nn
from transformers import AutoModelForVision2Seq, AutoProcessor


class Pix2Struct(nn.Module):
    def __init__(
            self,
            model_path='U4R/StructTable-base',
            max_new_tokens=1024,
            max_time=30,
            cache_dir=None,
            local_files_only=None,
            **kwargs,
        ):
        super().__init__()
        self.model_path = model_path
        self.max_new_tokens = max_new_tokens
        self.max_generate_time = max_time
        self.cache_dir = cache_dir
        self.local_files_only = local_files_only

        # init model and image processor from ckpt path
        self.init_image_processor(model_path)
        self.init_model(model_path)

        self.special_str_list = ['\\midrule', '\\hline']
        self.supported_output_format = ['latex']

    def postprocess_latex_code(self, code):
        for special_str in self.special_str_list:
            code = code.replace(special_str, special_str + ' ')
        return code

    def init_model(self, model_path):
        self.model = AutoModelForVision2Seq.from_pretrained(
            pretrained_model_name_or_path=model_path,
            cache_dir=self.cache_dir,
            local_files_only=self.local_files_only,
        )
        self.model.eval()

    def init_image_processor(self, image_processor_path):
        self.data_processor = AutoProcessor.from_pretrained(
            pretrained_model_name_or_path=image_processor_path,
            cache_dir=self.cache_dir,
            local_files_only=self.local_files_only,
        )

    def forward(self, image, **kwargs):
        # process image to tokens
        image_tokens = self.data_processor.image_processor(
            images=image,
            return_tensors='pt',
        )

        device = next(self.parameters()).device
        for k, v in image_tokens.items():
            image_tokens[k] = v.to(device)

        # generate text from image tokens
        model_output = self.model.generate(
            flattened_patches=image_tokens['flattened_patches'],
            attention_mask=image_tokens['attention_mask'],
            max_new_tokens=self.max_new_tokens,
            max_time=self.max_generate_time,
            no_repeat_ngram_size=20,
        )

        latex_codes = self.data_processor.batch_decode(model_output, skip_special_tokens=True)
        # postprocess
        for i, code in enumerate(latex_codes):
            latex_codes[i] = self.postprocess_latex_code(code)

        return latex_codes

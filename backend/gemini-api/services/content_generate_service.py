import uuid

import log_config ## logger 로그 남기기 위한 import (사용되고 있음)
import logging

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

class ContentGenerateService:
    client = genai.Client()


    
    # GENERATE TEXT
    async def generate_content(self, model, contents):
        response = self.client.models.generate_content(
            model=model,
            contents=contents
        )
        return response

    # GENERATE IMAGE
    async def generate_image(self, image_model, contents):
        response = self.client.models.generate_content(
            model=image_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
                )
        )

        saved_image_paths = []

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO((part.inline_data.data)))
                file_path = f"./images/{uuid.uuid4()}.png"
                image.save(file_path)
                saved_image_paths.append(file_path)

        return saved_image_paths
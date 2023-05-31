import time
import ddddocr
import uvicorn
import argparse
import base64
import requests
from fastapi import FastAPI, Form, File, UploadFile
import io
from PIL import Image

from pydantic import BaseModel

# 运行  可选参数如下
# --port 8124 指定端口,默认为8124
# --ocr 开启ocr模块 默认开启
# --old 只有ocr模块开启的情况下生效 默认不开启
# --det 开启目标检测模式

parser = argparse.ArgumentParser(description="使用ddddocr搭建的最简api服务")
parser.add_argument("-p", "--port", type=int, default=8124)
args = parser.parse_args()


class Ocr():
    ocr = ddddocr.DdddOcr()
    det = ddddocr.DdddOcr(det=True)
    slide = ddddocr.DdddOcr(det=False, ocr=False)

    @staticmethod
    def code_image(img: bytes):
        return Ocr.ocr.classification(img)

    @staticmethod
    def det_image(img: bytes):
        return Ocr.det.detection(img)

    @staticmethod
    def slide_image(target_img: bytes, background_img: bytes):
        try:
            imageStream = io.BytesIO(target_img)
            imageFile = Image.open(imageStream)
            background_img = imageFile.crop((0, 300, 240, 450))  # (x1, y1, x2, y2)
            cropped = imageFile.crop((0, 0, 240, 150))  # (x1, y1, x2, y2)
            return Ocr.slide.slide_comparison(ca(cropped), ca(background_img))
        except Exception as e:
            return Ocr.slide.slide_match(target_img, background_img)


def ocr_img(type, img_bytes, background_img_bytes):
    if type == 1:
        return Ocr.code_image(img_bytes)
    elif type == 2:
        return Ocr.det_image(img_bytes)
    elif type == 3:
        return Ocr.slide_image(
            img_bytes, background_img_bytes)
    else:
        return None

def ca(img):
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format='PNG', subsampling=0, quality=100)
    img_byte_array = img_byte_array.getvalue()
    return img_byte_array

app = FastAPI()


class Item(BaseModel):
    type: int = 1  # 1英数 2点选 3滑块
    img: str
    backgroundImg: str = None  # 滑块背景


@app.post("/ocr")
async def ocr_image(item: Item):
    """ 识别Base64编码图片 """
    try:
        type = item.type
        img_bytes = base64.b64decode(item.img, altchars=None, validate=False)
        background_img_bytes = bytes()
        if item.backgroundImg is not None:
            background_img_bytes = base64.b64decode(
                item.backgroundImg, altchars=None, validate=False)

        t = time.perf_counter()

        result = ocr_img(type, img_bytes, background_img_bytes)
        

        return {'code': 1, 'result': result, 'consumeTime': int((time.perf_counter() - t)*1000), 'msg': 'success'}
    except Exception as e:
        return {'code': 0, 'result': None, 'msg': str(e).strip()}


@app.post("/ocr/file")
async def ocr_image_file(type: int = Form(1), img: UploadFile = File(None), backgroundImg: UploadFile = File(None)):
    """ 识别文件上传图片 """
    try:
        img_bytes = await img.read()
        background_img_bytes = bytes()
        if backgroundImg is not None:
            background_img_bytes = await backgroundImg.read()

        t = time.perf_counter()
        result = ocr_img(type, img_bytes, background_img_bytes)

        return {'code': 1, 'result': result, 'consumeTime': int((time.perf_counter() - t)*1000), 'msg': 'success'}
    except Exception as e:
        return {'code': 0, 'result': None, 'msg': str(e).strip()}


@app.get("/ping")
def ping():
    return {'code' : 200, "msg": "gotcha!!"}


@app.get("/docr")
async def read_item(url: str, type: int = 1):
  try:
    img = requests.get(url, timeout=5).content
  except requests.exceptions.Timeout:
    return "timeout"
  t = time.perf_counter()
  code = ocr_img(type, img, bytes())
  return {'code': 1, 'from': url, 'result': code, 'consumeTime': int((time.perf_counter() - t)*1000), 'msg': 'success'}
    



if __name__ == '__main__':
    uvicorn.run(app='main:app', host="0.0.0.0",
                port=args.port, reload=False)

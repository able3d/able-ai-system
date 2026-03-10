import pytesseract
from PIL import Image
from pdf2image import convert_from_path


def extract_text_from_pdf(pdf_path):

    text_output = ""

    try:
        images = convert_from_path(pdf_path)

        for image in images:
            text = pytesseract.image_to_string(image)
            text_output += text + "\n"

    except Exception as e:
        print("OCR error:", e)

    return text_output

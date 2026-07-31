import os
import re
import ctypes
from ctypes import wintypes
from PIL import Image
import pytesseract
import uiautomation as auto

# Configure Tesseract path (Default path for UB-Mannheim installer)
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Win32 API Definitions for 64-bit safety
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

user32.GetWindowDC.argtypes = [wintypes.HWND]
user32.GetWindowDC.restype = wintypes.HDC

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC

gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.PrintWindow.restype = wintypes.BOOL

gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
gdi32.GetDIBits.restype = ctypes.c_int

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int

def capture_background_window(hwnd, rect):
    """
    Captures the window backing store using PrintWindow API in the background.
    """
    width = rect.width()
    height = rect.height()
    
    # Create DC and Bitmap
    hdc_window = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_window, width, height)
    
    hold_bitmap = gdi32.SelectObject(hdc_mem, hbitmap)
    
    # PW_RENDERFULLCONTENT = 2
    success = user32.PrintWindow(hwnd, hdc_mem, 2)
    if not success:
        # Fallback to standard PrintWindow
        user32.PrintWindow(hwnd, hdc_mem, 0)
        
    # Get bitmap bits
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]
        
    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height  # Top-down DIB
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = 0 # BI_RGB
    
    buffer_size = width * height * 4
    buffer = ctypes.create_string_buffer(buffer_size)
    
    gdi32.GetDIBits(hdc_window, hbitmap, 0, height, buffer, ctypes.byref(header), 0)
    
    # Cleanup
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_window)
    
    # Create PIL Image
    im = Image.frombytes("RGBA", (width, height), buffer)
    return im

def preprocess_image(img):
    # Convert to grayscale
    img_gray = img.convert('L')
    
    # Resize 2x using Lanczos filter for high quality upscaling
    w, h = img_gray.size
    img_resized = img_gray.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
    
    # Binarization: thresholding to remove light-colored watermarks (e.g. Phoenix logo)
    img_bin = img_resized.point(lambda x: 0 if x < 180 else 255, '1')
    return img_bin

def clean_thai_spaces(text):
    # Remove spaces that are between Thai characters
    text = re.sub(r'(?<=[\u0e00-\u0e7f])\s+(?=[\u0e00-\u0e7f])', '', text)
    # Correct common OCR misspellings for the word "เงิน"
    text = text.replace("เง็น", "เงิน").replace("เง้น", "เงิน").replace("เงืน", "เงิน").replace("เงน", "เงิน")
    return text

def do_ocr_on_item(win_hwnd, win_rect, item_rect):
    """
    Crops the captured window image to the item's coordinates and runs Tesseract OCR.
    """
    # 1. Capture the entire window in the background
    win_img = capture_background_window(win_hwnd, win_rect)
    
    # 2. Calculate relative coordinates of the list item with padding and width limit
    left = item_rect.left - win_rect.left
    top = item_rect.top - win_rect.top
    
    # Crop only the left 450 pixels where the bubble is located to avoid Tesseract layout confusion
    width = min(item_rect.width(), 450)
    height = item_rect.height()
    
    # Add a small padding around the crop area for better OCR readability
    padding_x = 10
    padding_y = 5
    
    crop_left = max(0, left - padding_x)
    crop_top = max(0, top - padding_y)
    crop_right = min(win_rect.width(), left + width + (padding_x * 2))
    crop_bottom = min(win_rect.height(), top + height + (padding_y * 2))
    
    # 3. Crop the message bubble
    cropped_img = win_img.crop((crop_left, crop_top, crop_right, crop_bottom))
    
    # Preprocess image to clean watermarks and increase resolution
    processed_img = preprocess_image(cropped_img)
    
    # For debugging/verification
    os.makedirs("debug", exist_ok=True)
    cropped_img.save(os.path.join("debug", "last_message.png"))
    processed_img.save(os.path.join("debug", "last_message_processed.png"))
    
    # 4. Perform OCR with Thai and English support
    # --psm 6 works well for single column vertical structured text
    custom_config = r'--psm 6'
    try:
        text = pytesseract.image_to_string(processed_img, lang='tha+eng', config=custom_config)
        return clean_thai_spaces(text.strip())
    except Exception as e:
        print(f"OCR Error: {e}")
        print("Retrying with English language only...")
        # Fallback to English only if Thai pack is not fully registered in Tesseract
        text = pytesseract.image_to_string(processed_img, lang='eng', config=custom_config)
        return text.strip()

def test_ocr_window(window_title):
    """
    Finds the window, extracts the last list item, and performs OCR.
    """
    # Find LINE Window
    if window_title:
        line_window = auto.WindowControl(searchDepth=1, Name=window_title)
    else:
        line_window = auto.WindowControl(searchDepth=1, ClassName="ChatWindow")
        
    if not line_window.Exists(1):
        return {"error": f"Could not find window '{window_title}'"}
        
    hwnd = line_window.NativeWindowHandle
    
    # Find LcListView inside the chat window
    list_view = line_window.ListControl(ClassName="LcListView")
    if not list_view.Exists(1):
        return {"error": "Could not find chat list (LcListView) in the selected window."}
        
    list_items = list_view.GetChildren()
    if not list_items:
        return {"error": "No messages found in the chat."}
        
    # Filter out padding elements (too tall) and system messages/date separators (too short)
    valid_items = []
    for item in list_items:
        try:
            h = item.BoundingRectangle.height()
            if 100 < h < 600:
                valid_items.append(item)
        except:
            pass
            
    if not valid_items:
        return {"error": "Could not find any valid chat bubbles (all items filtered out)."}
        
    # Get the last valid message
    last_item = valid_items[-1]
    
    win_rect = line_window.BoundingRectangle
    item_rect = last_item.BoundingRectangle
    
    text = do_ocr_on_item(hwnd, win_rect, item_rect)
    return {"success": True, "text": text}

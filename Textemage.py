"""
TEXTEMAGE
version: 1.4
author: JD jaga
license: MIT
"""

import customtkinter as ctk
import tkinter
import os
import sys
from PIL import Image, ImageTk, UnidentifiedImageError, ImageEnhance, ImageFilter, ImageOps, ImageStat
import random
import pytesseract
import webbrowser
import io

ctk.set_default_color_theme(random.choice(['blue','green','dark-blue']))

root = ctk.CTk()
root.title("TEXTEMAGE")
root.geometry("900x500")
root.minsize(600,400)
root.rowconfigure(0, weight=1)
root.columnconfigure((0,1), weight=1)
root.bind("<1>", lambda event: event.widget.focus_set())

def resource(relative_path):
    # resource finder via pyinstaller
    base_path = getattr(
        sys,
        '_MEIPASS',
        os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

root.wm_iconbitmap()
icopath = ImageTk.PhotoImage(file=resource("icon.png"))
root.iconphoto(False, icopath)

file = ""
image = ""
previous = ""

def load_image():
    global file, image, img, previous
    if os.path.exists(file):
        previous = file
        if len(os.path.basename(file))>=30:
            open_button.configure(text=os.path.basename(file)[:30]+"..."+os.path.basename(file)[-3:])
        else:
            open_button.configure(text=os.path.basename(file))

        try:
            Image.open(file)
        except UnidentifiedImageError:
            tkinter.messagebox.showerror("Oops!", "Not a valid image file!")
            return

        img = Image.open(file)   
        image = ctk.CTkImage(img)
        label_image.configure(text="", image=image)
        image.configure(size=(label_image.winfo_height(),label_image.winfo_height()*img.size[1]/img.size[0]))
        try:
            tip.hide()
        except Exception:
            pass
    else:
        if previous!="":
            file = previous
            
def open_image():
    # open image file
    global file
    file = tkinter.filedialog.askopenfilename(filetypes =[('Images', ['*.png','*.jpg','*.jpeg','*.bmp','*.webp'])
                                                          ,('All Files', '*.*')])
    load_image()
    
def drop(event):
    """
    tkinter drag and drop not implemented for this python version
    as it needs extra packages and manual modification in some libraries
    """
    
    global file
    if os.path.splitext(event.data.replace("{","").replace("}", ""))[-1] in ['.png','.jpg','.jpeg','.bmp','.webp']:
        file = event.data.replace("{","").replace("}", "")
    else:
        return

    load_image()  
    
def resize_event(event):
    # dynamic resize of the image with UI
    global image
    if image!="":
        image.configure(size=(event.height,event.height*img.size[1]/img.size[0]))

def upscale_small_image(pil_img, min_width=1600):
    w, h = pil_img.size
    if w >= min_width:
        return pil_img
    scale = min_width / w
    new_size = (int(w * scale), int(h * scale))
    return pil_img.resize(new_size, Image.LANCZOS)

def enhance_blue_text(pil_img):
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
    r, g, b = pil_img.split()
    r = ImageEnhance.Contrast(r).enhance(2.0)
    g = ImageEnhance.Contrast(g).enhance(2.0)
    b_enhanced = ImageEnhance.Contrast(b).enhance(3.0)
    b_inverted = ImageOps.invert(b_enhanced)
    merged_blue = Image.merge('RGB', (b_inverted, b_inverted, b_inverted))
    gray_normal = ImageOps.grayscale(pil_img)
    gray_blue = ImageOps.grayscale(merged_blue)
    std_normal = ImageStat.Stat(gray_normal).stddev[0]
    std_blue = ImageStat.Stat(gray_blue).stddev[0]
    if std_blue > std_normal * 1.05:
        return merged_blue
    return pil_img

def preprocess_for_ocr(pil_img):
    if pil_img.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', pil_img.size, (255, 255, 255))
        if pil_img.mode == 'P':
            pil_img = pil_img.convert('RGBA')
        bg.paste(pil_img, mask=pil_img.split()[-1] if pil_img.mode in ('RGBA', 'LA') else None)
        pil_img = bg
    elif pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
    pil_img = upscale_small_image(pil_img, min_width=1600)
    try:
        pil_img = enhance_blue_text(pil_img)
    except Exception:
        pass
    gray = ImageOps.grayscale(pil_img)
    auto = ImageOps.autocontrast(gray, cutoff=1)
    sharp = ImageEnhance.Sharpness(auto).enhance(2.0)
    contrast = ImageEnhance.Contrast(sharp).enhance(1.5)
    bright = ImageEnhance.Brightness(contrast).enhance(1.05)
    denoised = bright.filter(ImageFilter.MedianFilter(size=1))
    try:
        thresh_val = ImageStat.Stat(denoised).median[0]
        denoised = denoised.point(lambda x: 0 if x < thresh_val else 255, '1').convert('L')
    except Exception:
        pass
    return denoised

def preprocess_variants(pil_img):
    variants = []
    try:
        main = preprocess_for_ocr(pil_img)
        variants.append(main)
    except Exception:
        pass
    try:
        if pil_img.mode != 'RGB':
            pil_img_rgb = pil_img.convert('RGB')
        else:
            pil_img_rgb = pil_img.copy()
        w, h = pil_img_rgb.size
        if w < 2000:
            big = pil_img_rgb.resize((int(w*2), int(h*2)), Image.LANCZOS)
        else:
            big = pil_img_rgb
        gray_big = ImageOps.grayscale(big)
        contrast_big = ImageEnhance.Contrast(gray_big).enhance(2.0)
        sharp_big = ImageEnhance.Sharpness(contrast_big).enhance(3.0)
        variants.append(sharp_big)
    except Exception:
        pass
    try:
        if pil_img.mode != 'RGB':
            inv = pil_img.convert('RGB')
        else:
            inv = pil_img.copy()
        inv = upscale_small_image(inv, 1600)
        inv = ImageOps.invert(inv)
        inv_gray = ImageOps.grayscale(inv)
        inv_proc = ImageEnhance.Contrast(inv_gray).enhance(1.8)
        variants.append(inv_proc)
    except Exception:
        pass
    if not variants:
        variants.append(pil_img)
    return variants

def ocr_with_config(pil_img, psm, lang='eng'):
    config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
    try:
        return pytesseract.image_to_string(pil_img, lang=lang, config=config)
    except Exception:
        return ""

def pick_best_result(results):
    def score(text):
        if not text:
            return 0
        clean = text.strip()
        if not clean:
            return 0
        words = clean.split()
        alpha_count = sum(c.isalpha() for c in clean)
        digit_count = sum(c.isdigit() for c in clean)
        printable = sum(c.isprintable() or c in '\n\t ' for c in clean)
        s = (len(words) * 2 + alpha_count + digit_count * 0.5 + printable * 0.2)
        if len(clean) > 0:
            s += (alpha_count + digit_count) / len(clean) * 50
        return s
    scored = [(score(r), r) for r in results if r and r.strip()]
    if not scored:
        return ""
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]

def convert():
    # do the conversion with enhanced preprocessing
    global processing_label
    if not file:
        return
    try:
        processing_label.configure(text="Processing...")
        root.update_idletasks()
        variants = preprocess_variants(img)
        psm_modes = [6, 11, 4, 3, 7]
        all_results = []
        for v in variants:
            for psm in psm_modes:
                txt = ocr_with_config(v, psm)
                if txt and txt.strip():
                    all_results.append(txt)
        result = pick_best_result(all_results)
        if not result:
            try:
                result = pytesseract.image_to_string(img, config='--oem 3 --psm 3')
            except Exception:
                result = ""
    except pytesseract.TesseractNotFoundError:
        tkinter.messagebox.showerror("Missing Tesseract-OCR!",
                                     "Tesseract is not installed or it's not in your PATH")
        processing_label.configure(text="Ready")
        return
    except Exception as e:
        try:
            result = pytesseract.image_to_string(img)
        except Exception:
            tkinter.messagebox.showerror("OCR Error", str(e))
            processing_label.configure(text="Ready")
            return

    text_box.delete(1.0, tkinter.END)
    text_box.insert(tkinter.END, result)
    processing_label.configure(text=f"Ready | {len(result.split())} words extracted")
    
def do_popup(event, frame):
    try: frame.tk_popup(event.x_root, event.y_root)
    finally: frame.grab_release()

def paste():
    try:
        text_box.index(text_box.insert(tkinter.END, root.clipboard_get()))
    except:
        pass
    
def cut_text():
    """ cut text operation """
    copy_text()
    try: text_box.delete(tkinter.SEL_FIRST, tkinter.SEL_LAST)
    except: pass
    
def copy_text():
    """ copy text operation """
    root.clipboard_clear()
    try: root.clipboard_append(text_box.get(tkinter.SEL_FIRST, tkinter.SEL_LAST))
    except: pass

def paste_text():
    """ paste text operation """
    try: text_box.insert(text_box.index('insert'), root.clipboard_get())
    except: pass

def clear_text():
    """ clears the textbox """
    text_box.delete("1.0","end")

      
if ctk.get_appearance_mode()=="Dark":
    o = 1
else:
    o = 0
    
def new_window():
    # About window 
    label_header.configure(state="disabled")
    
    def exit_top_level():
        top_level.destroy()
        label_header.configure(state="normal")
        
    def web(link):
        webbrowser.open_new_tab(link)
        
    top_level = ctk.CTkToplevel(root)
    top_level.protocol("WM_DELETE_WINDOW", exit_top_level)
    top_level.minsize(400,200)
    top_level.title("About")
    top_level.resizable(width=False, height=False)
    top_level.transient(root)
    top_level.wm_iconbitmap()
    top_level.after(200, lambda: top_level.iconphoto(False, icopath))
    
    label_top = ctk.CTkLabel(top_level, text="Textemage v1.4", font=("Roboto",15))
    label_top.grid(padx=20, pady=20, sticky="w")

    try:
        version = str(pytesseract.get_tesseract_version())[:5]
    except:
        version = "Unknown"
        
    desc = "Tesseract version: "+version+"\n\nDeveloped by Akash Bora (Akascape) \nLicense: MIT \nCopyright 2023 "
    label_disc = ctk.CTkLabel(top_level,  text=desc, justify="left", font=("Roboto",12))
    label_disc.grid(padx=20, pady=0, sticky="w")
    
    label_logo = ctk.CTkLabel(top_level, text="", image=logo)
    label_logo.place(x=230,y=20)
    
    link = ctk.CTkLabel(top_level, text="Official Page", justify="left", font=("",13), text_color=("blue", "light blue"))
    link.grid(padx=20, pady=0, sticky="w")   
    link.bind("<Enter>", lambda event: link.configure(font=("", 13, "underline"), cursor="hand2"))
    link.bind("<Leave>", lambda event: link.configure(font=("", 13), cursor="arrow"))

DIRPATH = os.getcwd()


if os.path.exists(os.path.join(DIRPATH,"tesseract_path.txt")):
    with open(os.path.join(DIRPATH,"tesseract_path.txt"), 'r') as tfile:
        patht = tfile.read().strip()
        pytesseract.pytesseract.tesseract_cmd = patht
        tfile.close()
else:
    pytesseract.pytesseract.tesseract_cmd = "tesseract"

logo = ctk.CTkImage(Image.open(resource("icon.png")), size=(150,150)) 
frame_1 = ctk.CTkFrame(root)
frame_1.grid(row=0, column=0, sticky="news", padx=20, pady=20)
frame_1.rowconfigure(2, weight=1)
frame_1.columnconfigure(0, weight=1)

frame_2 = ctk.CTkFrame(root)
frame_2.grid(row=0, column=1, sticky="news", padx=(0,20), pady=20)
frame_2.rowconfigure(1, weight=1)
frame_2.columnconfigure(0, weight=1)

label_header = ctk.CTkButton(frame_1, text="TEXTEMAGE", fg_color=ctk.ThemeManager.theme["CTkTextbox"]["fg_color"][o],
                             height=30, command=new_window, hover=False, corner_radius=30,
                             text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"][o])
label_header.grid(padx=10, pady=10)

open_button = ctk.CTkButton(frame_1, text="OPEN IMAGE SOURCE", command=open_image, corner_radius=30)
open_button.grid(padx=10, pady=10, sticky="nwe")

image_frame = ctk.CTkFrame(frame_1, corner_radius=20)
image_frame.grid(padx=10, pady=10, sticky="nwes")
image_frame.rowconfigure(0, weight=1)
image_frame.columnconfigure(0, weight=1)

label_image = ctk.CTkLabel(image_frame, text="➕", corner_radius=10)
label_image.grid(padx=10, pady=10, sticky="nwes")

#label_image.drop_target_register(DND_FILES)
#label_image.dnd_bind('<<Drop>>', drop)

image_frame.bind("<Configure>", resize_event)

convert_button = ctk.CTkButton(frame_1, text="EXTRACT", command=convert, corner_radius=30)
convert_button.grid(padx=10, pady=10, sticky="we")

processing_label = ctk.CTkLabel(frame_1, text="Ready", font=("", 11), height=20)
processing_label.grid(padx=10, pady=(0, 10), sticky="we")

label_2 = ctk.CTkLabel(frame_2, text="Converted text will be shown here")
label_2.grid(padx=10, pady=10)

text_box = ctk.CTkTextbox(frame_2)
text_box.grid(sticky="news", padx=10, pady=10)
text_box._textbox.configure(selectbackground=root._apply_appearance_mode(open_button._fg_color))

RightClickMenu = tkinter.Menu(text_box, tearoff=False, fg=ctk.ThemeManager.theme["CTkLabel"]["text_color"][o],
                              background=ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"][o],
                              activebackground=root._apply_appearance_mode(open_button._fg_color))
RightClickMenu.add_command(label="cut", command=cut_text)
RightClickMenu.add_command(label="copy", command=copy_text)
RightClickMenu.add_command(label="paste", command=paste_text)
RightClickMenu.add_command(label="clear", command=clear_text)
text_box.bind("<Button-3>", lambda event: do_popup(event, frame=RightClickMenu))

root.mainloop()

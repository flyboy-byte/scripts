#!/usr/bin/env python3
"""
Neofetch Desktop Background Generator - Live Wallpaper Service
"""
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import time
import shutil
import glob
from datetime import datetime

def check_dependencies():
    try:
        from PIL import Image
    except ImportError:
        sys.exit(1)

def get_neofetch_output():
    try:
        result = subprocess.run([
            'neofetch', 
            '--stdout',
            '--color_blocks', 'off',
            '--ascii_colors', 'off'
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        sys.exit(1)

def get_system_font():
    font_paths = [
        '/usr/share/fonts/TTF/DejaVuSansMono.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        '/usr/share/fonts/TTF/JetBrainsMono-Regular.ttf',
        '/usr/share/fonts/TTF/FiraCode-Regular.ttf',
        '/usr/share/fonts/TTF/SourceCodePro-Regular.ttf',
        '/usr/share/fonts/liberation/LiberationMono-Regular.ttf',
        '/usr/share/fonts/noto/NotoSansMono-Regular.ttf',
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            return font_path
    return None

def clear_wallpaper_directory(wallpaper_dir):
    try:
        if os.path.exists(wallpaper_dir):
            files = glob.glob(os.path.join(wallpaper_dir, '*'))
            for file in files:
                if os.path.isfile(file):
                    os.remove(file)
        else:
            os.makedirs(wallpaper_dir, exist_ok=True)
    except Exception:
        pass

def create_wallpaper(neofetch_text, width=1920, height=1080, output_file='/home/logan/Downloads/wallpaper/wallpaper_1.png'):
    img = Image.new('RGB', (width, height), color='#1e1e2e')
    draw = ImageDraw.Draw(img)
    
    font_path = get_system_font()
    try:
        if font_path:
            font_size = max(12, min(16, height // 80))
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Add current date/time to neofetch output
    current_time = datetime.now().strftime("%A, %B %d, %Y - %I:%M:%S %p")
    neofetch_text += f"\n\n{current_time}"
    
    lines = neofetch_text.split('\n')
    wrapped_lines = []
    max_chars = width // 8
    
    for line in lines:
        if len(line) > max_chars:
            wrapped = textwrap.fill(line, width=max_chars)
            wrapped_lines.extend(wrapped.split('\n'))
        else:
            wrapped_lines.append(line)
    
    line_height = font.getbbox('A')[3] + 4
    total_text_height = len(wrapped_lines) * line_height
    start_y = (height - total_text_height) // 2
    
    max_line_width = 0
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        max_line_width = max(max_line_width, line_width)
    
    start_x = (width - max_line_width) // 2
    
    padding = 40
    rect_x1 = start_x - padding
    rect_y1 = start_y - padding
    rect_x2 = start_x + max_line_width + padding
    rect_y2 = start_y + total_text_height + padding
    
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [rect_x1, rect_y1, rect_x2, rect_y2], 
        radius=15, 
        fill=(30, 30, 46, 180)
    )
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    current_y = start_y
    for line in wrapped_lines:
        color = '#cdd6f4'
        
        if ':' in line:
            if any(keyword in line.lower() for keyword in ['os', 'host', 'kernel']):
                color = '#89b4fa'
            elif any(keyword in line.lower() for keyword in ['cpu', 'gpu', 'memory']):
                color = '#a6e3a1'
            elif any(keyword in line.lower() for keyword in ['shell', 'terminal', 'de', 'wm']):
                color = '#fab387'
        elif line.strip().startswith('███'):
            color = '#f38ba8'
        elif any(day in line for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
            color = '#f9e2af'
        
        draw.text((start_x, current_y), line, fill=color, font=font)
        current_y += line_height
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    img.save(output_file, 'PNG', quality=95)
    return output_file

def apply_wallpaper(wallpaper_path):
    try:
        time.sleep(0.1)
        result = subprocess.run([
            'plasma-apply-wallpaperimage', 
            wallpaper_path
        ], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def main():
    check_dependencies()
    
    width, height = 1920, 1080
    wallpaper_dir = '/home/logan/Downloads/wallpaper'
    
    iteration = 0
    wallpaper_counter = 1
    last_neofetch_output = None
    
    try:
        while True:
            iteration += 1
            start_time = time.time()
            
            try:
                neofetch_text = get_neofetch_output()
                
                if neofetch_text != last_neofetch_output:
                    clear_wallpaper_directory(wallpaper_dir)
                    output_file = os.path.join(wallpaper_dir, f'wallpaper_{wallpaper_counter}.png')
                    create_wallpaper(neofetch_text, width, height, output_file)
                    apply_wallpaper(output_file)
                    last_neofetch_output = neofetch_text
                    wallpaper_counter += 1
                    
                    # Reset counter every 1000 iterations
                    if wallpaper_counter > 1000:
                        wallpaper_counter = 1
                
            except Exception:
                pass
            
            elapsed = time.time() - start_time
            sleep_time = max(0, 15.0 - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        pass
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Neofetch Desktop Background Generator
Creates a stylized desktop wallpaper using neofetch system information
"""

import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
from datetime import datetime

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow is not installed")
        print("Install with: pip install pillow")
        sys.exit(1)

def get_neofetch_output():
    """Capture neofetch output without ANSI escape sequences"""
    try:
        # Get clean neofetch output without color codes
        result = subprocess.run([
            'neofetch', 
            '--stdout',  # Output to stdout instead of terminal
            '--color_blocks', 'off',  # Disable color blocks
            '--ascii_colors', 'off'   # Disable ASCII colors
        ], capture_output=True, text=True, check=True)
        
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running neofetch: {e}")
        sys.exit(1)

def get_system_font():
    """Get a suitable monospace font for Arch Linux"""
    font_paths = [
        # Common Arch Linux fonts
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

def create_wallpaper(neofetch_text, width=1920, height=1080, output_file='neofetch_wallpaper.png'):
    """Create a desktop wallpaper with neofetch information"""
    
    # Create image with dark background
    img = Image.new('RGB', (width, height), color='#1e1e2e')
    draw = ImageDraw.Draw(img)
    
    # Try to load a monospace font
    font_path = get_system_font()
    try:
        if font_path:
            font_size = max(12, min(16, height // 80))  # Responsive font size
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Split the text into lines and wrap long lines
    lines = neofetch_text.split('\n')
    wrapped_lines = []
    max_chars = width // 8  # Approximate character width
    
    for line in lines:
        if len(line) > max_chars:
            wrapped = textwrap.fill(line, width=max_chars)
            wrapped_lines.extend(wrapped.split('\n'))
        else:
            wrapped_lines.append(line)
    
    # Calculate text positioning
    line_height = font.getbbox('A')[3] + 4  # Height of 'A' plus some padding
    total_text_height = len(wrapped_lines) * line_height
    
    # Center the text vertically
    start_y = (height - total_text_height) // 2
    
    # Find the longest line for horizontal centering
    max_line_width = 0
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        max_line_width = max(max_line_width, line_width)
    
    start_x = (width - max_line_width) // 2
    
    # Add a subtle background rectangle for better readability
    padding = 40
    rect_x1 = start_x - padding
    rect_y1 = start_y - padding
    rect_x2 = start_x + max_line_width + padding
    rect_y2 = start_y + total_text_height + padding
    
    # Draw semi-transparent background rectangle
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [rect_x1, rect_y1, rect_x2, rect_y2], 
        radius=15, 
        fill=(30, 30, 46, 180)  # Semi-transparent dark background
    )
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # Draw the text
    current_y = start_y
    for line in wrapped_lines:
        # Use different colors for different types of information
        color = '#cdd6f4'  # Default light color
        
        if ':' in line:
            # This looks like a key-value pair
            if any(keyword in line.lower() for keyword in ['os', 'host', 'kernel']):
                color = '#89b4fa'  # Blue for system info
            elif any(keyword in line.lower() for keyword in ['cpu', 'gpu', 'memory']):
                color = '#a6e3a1'  # Green for hardware
            elif any(keyword in line.lower() for keyword in ['shell', 'terminal', 'de', 'wm']):
                color = '#fab387'  # Orange for environment
        elif line.strip().startswith('███'):
            color = '#f38ba8'  # Pink for ASCII art elements
        
        draw.text((start_x, current_y), line, fill=color, font=font)
        current_y += line_height
    
    # Add timestamp in bottom right corner
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_text = f"Generated: {timestamp}"
    
    bbox = draw.textbbox((0, 0), timestamp_text, font=font)
    timestamp_width = bbox[2] - bbox[0]
    timestamp_height = bbox[3] - bbox[1]
    
    draw.text(
        (width - timestamp_width - 20, height - timestamp_height - 20), 
        timestamp_text, 
        fill='#6c7086',  # Subtle gray
        font=font
    )
    
    # Add title at the top
    title = "System Information"
    title_bbox = draw.textbbox((0, 0), title, font=font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(
        ((width - title_width) // 2, 30), 
        title, 
        fill='#f9e2af',  # Yellow for title
        font=font
    )
    
    # Save the image
    img.save(output_file, 'PNG', quality=95)
    print(f"Wallpaper saved as: {output_file}")
    print(f"Resolution: {width}x{height}")
    return output_file

def main():
    """Main function to generate the wallpaper"""
    check_dependencies()
    
    print("Generating neofetch wallpaper...")
    
    # Get neofetch output
    neofetch_text = get_neofetch_output()
    
    # Get screen resolution (optional)
    # You can modify these values or detect them automatically
    resolutions = {
        '1080p': (1920, 1080),
        '1440p': (2560, 1440),
        '4K': (3840, 2160),
        '1366x768': (1366, 768),
    }
    
    # Default to 1080p, but you can change this
    width, height = resolutions['1080p']
    
    # Create the wallpaper
    output_file = f'neofetch_wallpaper_{width}x{height}.png'
    create_wallpaper(neofetch_text, width, height, output_file)
    
    print("\nTo set as wallpaper:")
    print("Linux (GNOME): gsettings set org.gnome.desktop.background picture-uri file://$(pwd)/" + output_file)
    print("Linux (KDE): Right-click desktop → Configure Desktop → Wallpaper → Add Image")
    print("macOS: Right-click desktop → Change Desktop Background")
    print("Windows: Right-click desktop → Personalize → Background")

if __name__ == "__main__":
    main()
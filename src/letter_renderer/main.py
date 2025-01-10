import math
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

class PointCollectorPen(BasePen):
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.paths = []  # List of paths (each path is a list of points)
        self.currentPath = []  # Points for the current path

    def _moveTo(self, pt):
        if self.currentPath:
            self.paths.append(self.currentPath)
            self.currentPath = []
        self.currentPath.append(pt)

    def _lineTo(self, pt):
        self.currentPath.append(pt)

    def _curveToOne(self, pt1, pt2, pt3):
        # For G-code, approximate curves with straight lines
        # Break into line segments (you can refine this)
        self.currentPath.extend([pt1, pt2, pt3])

    def _closePath(self):
        if self.currentPath:
            self.paths.append(self.currentPath)
            self.currentPath = []

    def getPaths(self):
        if self.currentPath:
            self.paths.append(self.currentPath)
        return self.paths

# Load the font and extract points for a string
def get_paths_for_line(font_path, text, scale=1.0, origin=(0, 0)):
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()  # Character-to-glyph mapping
    pen = PointCollectorPen(glyph_set)

    all_paths = []
    x_offset = 0  # Used to space characters
    for char in text:
        glyph_name = cmap.get(ord(char))
        if not glyph_name:
            continue  # Skip unknown characters
        glyph = glyph_set[glyph_name]
        
        pen.paths = []  # Reset paths for each character
        glyph.draw(pen)
        char_paths = pen.getPaths()
        
        # Apply x_offset and scaling
        for path in char_paths:
            all_paths.append([(x * scale + x_offset + origin[0], y * scale + origin[1]) for x, y in path])

        # Update x_offset for the next character
        x_offset += glyph.width * scale

    return all_paths

def paths_to_gcode(paths, feedrate=6000, pen_down="M3", pen_up="M5", start_gcode="G21", end_gcode="G1 X0 Y0 F3000"):
    bed_size = (125, 125)
    print("Converting paths to gcode...")
    gcode = start_gcode
    gcode += f"{pen_up}\n"
    gcode += f"G1 F{feedrate}\n"
    for path in paths:
        if path[0][0] > bed_size[0] or path[0][1] > bed_size[1]:
            print(f"Warning: Path start out of bounds: ({path[0][0]:.2f}, {path[0][1]:.2f})")
            path[0] = (min(path[0][0], bed_size[0]), min(path[0][1], bed_size[1]))
            print(f"Clamped to: ({path[0][0]:.2f}, {path[0][1]:.2f})")
        gcode += f"G0 X{path[0][0]:.2f} Y{path[0][1]:.2f}\n"
        gcode += f"{pen_down}\n"
        for x, y in path[1:]:
            if x > bed_size[0] or y > bed_size[1]:
                print(f"Warning: Path out of bounds: ({x:.2f}, {y:.2f})")
                x = min(x, bed_size[0])
                y = min(y, bed_size[1])
                print(f"Clamped to: ({x:.2f}, {y:.2f})")
            gcode += f"G1 X{x:.2f} Y{y:.2f}\n"
        gcode += f"{pen_up}\n"
    gcode += end_gcode
    print("Gcode conversion complete!")
    return gcode

def wrap_text(font, scale, message, max_width):
    # Wrap text to fit within a maximum width
    # Split text into lines
    existing_lines = message.splitlines(True)
    wrapped_lines = []
    for existing_line in existing_lines:
        if not existing_line.strip():
            wrapped_lines.append("")
            continue
        words = existing_line.split()
        current_line = []
        current_width = 0
        for word in words:
            word_width = get_text_width(font, scale, word)
            if current_width + word_width > max_width:
                wrapped_lines.append(" ".join(current_line))
                current_line = []
                current_width = 0
            current_line.append(word)
            current_width += word_width

        if current_line:
            wrapped_lines.append(" ".join(current_line))

    # for line in wrapped_lines:
    #     print(line)

    return wrapped_lines

def get_text_width(font, scale, text):
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()  # Character-to-glyph mapping

    width = 0
    for char in text:
        glyph_name = cmap.get(ord(char))
        if not glyph_name:
            continue  # Skip unknown characters
        glyph = glyph_set[glyph_name]
        width += glyph.width * scale

    return width

def construct_postcard_paths(font_path, message, address, isInternational=False, show_outline=False):
    # postcard is 152.4 mm x 101.6 mm (6 in x 4 in)
    # message starts at 6.35, 88.9 mm (0.25, 3.5 in), is left-aligned, and has a maximum width of 63.5 mm (2.5 in)
    # address starts at 82.55, 50.8 mm (3.25, 2 in), and is left-aligned
    # a domestic stamp square is 19.05 mm x 19.05 mm (0.75 in x 0.75 in) and has a margin of 6.35 mm (0.25 in) from the right and top edges
    # an international stamp is a 0.75in circle with a margin of 12.7 mm (0.5 in) from the right and top edges, with INTL in the center
    print("Constructing postcard paths")
    print("Loading font...")
    font = TTFont(font_path)
    message_scale = 0.005
    message_origin = (6.35, 88.9)
    address_scale = 0.004
    address_origin = (82.55, 50.8)
    stamp_origin = (152.4 - 6.35 - 19.05, 101.6 - 6.35 - 19.05)
    stamp_text = "INTL" if isInternational else "USA"
    stamp_text_origin = (152.4 - 6.35 - 6*19.05/7, 101.6 - 6.35 - 3*19.05/5)

    print("wrapping messsage...")
    message_lines = wrap_text(font, message_scale, message, 55) # wrapping isn't harsh enough, so overdo it here to compensate
    # don't wrap address
    address_lines = address.splitlines()

    print("computing message paths...")
    message_paths = []
    for i, line in enumerate(message_lines):
        message_paths.extend(get_paths_for_line(font_path, line, message_scale, (message_origin[0], message_origin[1] - i * 5)))

    print("computing address paths...")
    address_paths = []
    for i, line in enumerate(address_lines):
        address_paths.extend(get_paths_for_line(font_path, line, address_scale, (address_origin[0], address_origin[1] - i * 5)))
    
    print("computing stamp paths...")
    stamp_paths = get_paths_for_line(font_path, stamp_text, message_scale, stamp_text_origin)
    if isInternational:
        # circle stamp
        # approximate circle with a 20-sided polygon
        stamp_paths.append([(stamp_origin[0] + 19.05/2 + 19.05/2 * math.cos(2 * math.pi * i / 20), stamp_origin[1] + 19.05/2 + 19.05/2 * math.sin(2 * math.pi * i / 20)) for i in range(21)])
    else:
        # square stamp
        stamp_paths.append([(stamp_origin[0], stamp_origin[1]), (stamp_origin[0] + 19.05, stamp_origin[1]), (stamp_origin[0] + 19.05, stamp_origin[1] + 19.05), (stamp_origin[0], stamp_origin[1] + 19.05), (stamp_origin[0], stamp_origin[1])])
    
    outline_paths = []
    if show_outline:
        outline_paths.append([(0, 0), (152.4, 0), (152.4, 101.6), (0, 101.6), (0, 0)])

    print("paths constructed!")
    result = message_paths + address_paths + stamp_paths + outline_paths
    return result

if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv(override=True)
    import os
    
    font_path = os.getenv("FONT_PATH")
    message = "Hi Fiona!\n\nI saw you shipped your <PROJECT_NAME> project. I'm so excited for you! Keep up the great work, and I can't wait to see what else you make.\n\n-The Postcard Writer"
    paths = construct_postcard_paths(font_path, message, "Fiona Hackworth\n1234 Main St\nCity, State 12345")
    gcode = paths_to_gcode(paths)
    with open("postcard.gcode", "w") as f:
        f.write(gcode)
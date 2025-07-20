import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
import os
import json

def plot_code(text_widget, gmfile):
    # Regex-based simple highlighter
    def apply_syntax_highlighting():
        def apply_tag(tag, match):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            text_widget.tag_add(tag, start, end)

        code = text_widget.get("1.0", tk.END)

        global FUNCTIONS
        for match in re.finditer(r"\b(" + "|".join(map(re.escape, FUNCTIONS)) + r")\b", code):
            apply_tag("function", match)
        
        global BUILTINS
        for match in re.finditer(r"\b(" + "|".join(map(re.escape, BUILTINS)) + r")\b", code):
            apply_tag("builtin", match)

        global RESOURCES
        for match in re.finditer(r"\b(" + "|".join(map(re.escape, RESOURCES)) + r")\b", code):
            apply_tag("resource", match)

        global SCRIPTS
        for match in re.finditer(r"\b(" + "|".join(map(re.escape, SCRIPTS)) + r")\b", code):
            apply_tag("script", match)
        
        global ENUM_NAMES
        for match in re.finditer(r"\b(" + "|".join(map(re.escape, ENUM_NAMES)) + r")\b", code):
            apply_tag("enum_name", match)
        
        global ENUM_ENTRIES
        for match in re.finditer(r"\b(" + "|".join(map(re.escape, ENUM_ENTRIES)) + r")\b", code):
            apply_tag("enum_entry", match)
        
        global MACROS
        for match in re.finditer(r"\b(" + "|".join(map(re.escape, MACROS)) + r")\b", code):
            apply_tag("macro", match)

        global GLOBALVARS
        for match in re.finditer(r"\b(" + "|".join(map(re.escape, GLOBALVARS)) + r")\b", code):
            apply_tag("globalvar", match)

        # Keywords
        keywords = [
            "var", "globalvar",
            "enum",
            "discard", "attribute", "varying", "uniform", "const", "in", "out", "inout"
            "float", "int", "void", "bool",
            "lowp", "mediump", "highp", "precision", "invariant",
            "mat2", "mat3", "mat4",
            "vec2", "vec3", "vec4",
            "ivec2", "ivec3", "ivec4",
            "bvec2", "bvec3", "bvec4",
            "sampler2D", "samplerCube", "struct",
            "function", "break", "continue", "return", "do", "if", "else", "for", "while", "until", "with", "try", "catch", "new", "and", "or", "not", "delete"
        ]

        for match in re.finditer(r"\b(" + "|".join(map(re.escape, keywords)) + r")\b", code):
            apply_tag("keyword", match)
        
        for match in re.finditer(r"(\{|\})", code):
            apply_tag("keyword", match)
        
        for match in re.finditer(r"(\#macro)\b", code):
            apply_tag("keyword", match)

        for match in re.finditer(r"(?:0x[0-9a-fA-F]+|\$[0-9a-fA-F]+|#[0-9a-fA-F]+|b[0-1]+|\d+\.?\d*|\.\d+)\b", code):
            apply_tag("value", match)

        # Strings
        for match in re.finditer(r"(\".*?\"|\'.*?\')", code):
            apply_tag("string", match)

        # Comments
        for match in re.finditer(r"//.*", code):
            apply_tag("comment", match)

    text_widget.delete("1.0", tk.END)
    text_widget.insert(tk.END, gmfile.content)
    apply_syntax_highlighting()

def plot_dict(ax, d, path=""):
    def sum_dict(d):
        if not isinstance(d, dict):
            return d.line_count
        
        s = 0

        for k, v in d.items():
            if isinstance(v, dict):
                s += sum_dict(v)
            else:
                s += v.line_count

        return s
    
    ax.clear()

    labels = []
    values = []

    for k, v in d.items():
        labels.append(k)
        values.append(sum_dict(v))
    
    total = sum(values)

    ax.pie(values, labels=labels, autopct=lambda p: '{:.0f}\n({:.1f}%)'.format(p * total / 100, p) if p > 1 else '', startangle=140)

    global project_name

    ax.set_title(f"{project_name}{('/' if path!='' else '') + path}\nTotal lines: {total}")

    ax.axis('equal')

def populate_tree(tree, parent, dictionary):
    for key, value in dictionary.items():
        if isinstance(value, dict):
            # Insert folder or file name as a tree node
            node = tree.insert(parent, 'end', text=key)

            # If this is a dictionary (i.e. subfolder), recurse to add its children
            populate_tree(tree, node, value)
        else:
            tree.insert(parent, 'end', text=key)

def launch(_project_name, files, resources, scripts, enum_names, enum_entries, macros, globalvars):
    global project_name
    project_name = _project_name
    
    global BUILTINS
    global FUNCTIONS
    global RESOURCES
    global SCRIPTS
    global ENUM_NAMES
    global ENUM_ENTRIES
    global MACROS
    global GLOBALVARS

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "builtins.txt"), 'r') as f:
        BUILTINS = [line.rstrip('\n') for line in f.readlines()]
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "functions.txt"), 'r') as f:
        FUNCTIONS = [line.rstrip('\n') for line in f.readlines()]
    
    RESOURCES = resources
    SCRIPTS = scripts
    ENUM_NAMES = enum_names
    ENUM_ENTRIES = enum_entries
    MACROS = macros
    GLOBALVARS = globalvars

    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)

    # Create main application window
    root = tk.Tk()
    root.title("gms2_stats")
    root.geometry("960x540")

    # Create a PanedWindow to split the left (tree) and right (pie chart) sections
    paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # Left pane: Treeview widget for folder structure
    left_pane = ttk.Frame(paned_window)
    tree = ttk.Treeview(left_pane)
    tree.heading("#0", text=project_name, anchor="w", command=lambda: on_tree_heading_click())
    populate_tree(tree, '', files)
    tree.pack(fill=tk.BOTH, expand=True)
    paned_window.add(left_pane, weight=1)

    # Right pane: will show either chart OR text
    right_pane = ttk.Frame(paned_window)
    paned_window.add(right_pane, weight=5)

    # Stack both widgets in same space
    content_frame = tk.Frame(right_pane)
    content_frame.pack(fill=tk.BOTH, expand=True)

    # 1. Matplotlib chart widget
    chart_frame = tk.Frame(content_frame)
    chart_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # 2. Text widget
    text_frame = tk.Frame(content_frame)
    text_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    text_widget = tk.Text(text_frame, wrap=tk.WORD)
    text_widget.insert(tk.END, "Here's your juicy data or code output.\nAll selectable!")
    text_widget.pack(fill=tk.BOTH, expand=True)

    # Text widget config
    text_widget.config(font=("Consolas", 10))
    # Load color config from JSON
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.json"), "r") as f:
        colors = json.load(f)

    text_widget.config(
        bg=colors["background"], 
        fg=colors["default_text"], 
        insertbackground=colors["cursor"]
    )

    for tag, color in colors["syntax"].items():
        text_widget.tag_config(tag, foreground=color)

    def show_content(ax, path=""):
        d = files
        
        if path != "":
            for f in path.split("/"):
                try:
                    d = d[f]
                except KeyError:
                    print(f'ERROR: Path "{path}" does not exist. Can\'t show plot.')
                    return
        
        if isinstance(d, dict):
            plot_dict(ax, d, path)

            canvas.draw()

            chart_frame.lift()
        else:
            plot_code(text_widget, d)

            text_frame.lift()
    
    # Function to get the full path of the selected item
    def get_full_path(item_id):
        path = []
        while item_id:  # Traverse up the tree using the parent() method
            path.append(tree.item(item_id, 'text'))
            item_id = tree.parent(item_id)
        return "/".join(reversed(path))  # Reverse the list to get root to leaf order

    def on_tree_heading_click():
        show_content(ax)

    def on_item_selected(event):
        # Get the selected item
        selected_item = tree.selection()[0]  # Get the first (and only) item from the selection
        # Retrieve the item's text (the folder or file name)
        full_path = get_full_path(selected_item)
        show_content(ax,full_path)

    # Function to handle window close
    def on_closing():
        root.quit()  # Stop the main loop
        root.destroy()  # Properly close the window and clean up resources

    # Bind the close button (X) to the on_closing function
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Bind the <<TreeviewSelect>> event to the on_item_selected function
    tree.bind("<<TreeviewSelect>>", on_item_selected)

    show_content(ax)

    # Start the Tkinter main event loop
    root.mainloop()

if __name__ == "__main__":
    print("Launch gms2_stats.py, not this file.")
    exit()
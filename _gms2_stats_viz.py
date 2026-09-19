import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Text
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
import json
from _gms2_stats_io import local_resource_path, load_file, GMFile

class SyntaxInfo:
    def __init__(self, resources, scripts, enum_names, enum_entries, macros, globalvars):
        self.resources = resources
        self.scripts = scripts
        self.enum_names = enum_names
        self.enum_entries = enum_entries
        self.macros = macros
        self.globalvars = globalvars

PROJECT_FILE = ""
PROJECT_NAME = "No project"
FILES = {}
SYNTAX = None
LANGUAGE_STYLES = None

def plot_code(text_widget: Text, gmfile: GMFile):
    # Regex-based highlighter
    def apply_syntax_highlighting():
        def apply_tag(tag, match):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            text_widget.tag_add(tag, start, end)

        code = text_widget.get("1.0", tk.END)

        global LANGUAGE_STYLES

        # Find syntax type of GMFile
        for language in LANGUAGE_STYLES.values():
            if gmfile.extension in language["extensions"]:
                break
        
        style = language["style"]

        # Update basic colours
        text_widget.config(font=("Consolas", 10, ))

        text_widget.config(
            bg=style["background"], 
            fg=style["default_text"]["colour"],
            font=("Consolas", 10, style["default_text"]["styling"]),
            insertbackground=style["cursor"],
            selectbackground=style["selectbackground"],
        )

        # Set colours of this style's syntax categories
        for tag, font in style["syntax"].items():
            text_widget.tag_config(tag, foreground=font["colour"], font=("Consolas", 10, font["styling"]))

        # Unique syntax features
        for feature_type, expressions in language["features"].items():
            for match in re.finditer(r"(?<!\w)(" + "|".join(map(re.escape, expressions)) + r")(?!\w)", code):
                apply_tag(feature_type, match)

        # Project-specific syntax highlights
        global SYNTAX
        
        syntax_map = {
            "resource": SYNTAX.resources,
            "script": SYNTAX.scripts,
            "enum_name": SYNTAX.enum_names,
            "enum_entry": SYNTAX.enum_entries,
            "macro": SYNTAX.macros,
            "globalvar": SYNTAX.globalvars
        }

        for tag_name, syntax_words in syntax_map.items():
            if syntax_words and tag_name in style["syntax"].keys():
                pattern = r"(?<!\w)(" + "|".join(map(re.escape, syntax_words)) + r")(?!\w)"
                for match in re.finditer(pattern, code):
                    apply_tag(tag_name, match)
        
        # Curly brackets
        for match in re.finditer(r"(\{|\})", code):
            apply_tag("keyword", match)

        # Values
        for match in re.finditer(r"(?<![A-Za-z_])(?:(?:0x|0b|#|\$)[0-9a-fA-F]+|\d+\.+\d+|\.\d+|\d+\.|\d+)(?![\d.])", code):
            apply_tag("value", match)

        # Strings
        for match in re.finditer(r'"(\\.|[^"\\])*"', code):
            apply_tag("string", match)

        # Single-line comments
        for match in re.finditer(r"//.*", code):
            apply_tag("comment", match)

        # Multi-line comments
        for match in re.finditer(r"/\*[\s\S]*?\*/", code):
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

    global PROJECT_NAME

    ax.set_title(f"{PROJECT_NAME}{('/' if path!='' else '') + path}\nTotal lines: {total}")

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

def update_app(project_name, files, syntax_info):
    global SYNTAX
    SYNTAX = SyntaxInfo(*syntax_info)
    
    global PROJECT_NAME
    global FILES
    PROJECT_NAME = project_name
    FILES = files

    # Update Treeview
    TREE.heading("#0", text=PROJECT_NAME)

    # Clear tree
    for row in TREE.get_children():
        TREE.delete(row)

    # Repopulate
    populate_tree(TREE, '', FILES)

def launch():
    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)

    # Create main application window
    root = tk.Tk()
    root.title("gms2_stats")
    root.geometry("960x540")

    # Set up the menu bar
    menu_bar = tk.Menu(root)

    ignore_extensions = tk.BooleanVar(root, value=True)

    # File menu
    def open_file():
        file_path = filedialog.askopenfilename(
            title="Choose GameMaker Studio 2 Project",
            filetypes=[("GameMaker Studio 2 Project File", "*.yyp")]
        )
        if file_path:
            result = load_file(file_path,ignore_extensions.get())

            if result.ok():
                global PROJECT_FILE
                PROJECT_FILE = file_path

                project_name, files, *syntax_info = result.info
                update_app(project_name, files, syntax_info)
                show_content(ax)
            else:
                messagebox.showerror("Error", result.error)

    def reload_file():
        global PROJECT_FILE

        if PROJECT_FILE == "":
            messagebox.showinfo("Info", "No project loaded")
        else:
            result = load_file(PROJECT_FILE, ignore_extensions.get())

            if result.ok():
                project_name, files, *syntax_info = result.info
                update_app(project_name, files, syntax_info)
                show_content(ax)
            else:
                messagebox.showerror("Error", result.error)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Open", command=open_file, accelerator="Ctrl+O")
    file_menu.add_command(label="Reload", command=reload_file, accelerator="Ctrl+R")
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit, accelerator="Alt+F4")

    # Add the File menu to the menu bar
    menu_bar.add_cascade(label="File", menu=file_menu)

    # Settings Button Menu
    options_menu = tk.Menu(menu_bar, tearoff=0)

    def on_ignore_extensions_changed():
        reload_file()

    options_menu.add_checkbutton(
        label="Ignore Extensions",
        variable=ignore_extensions,
        onvalue=True,
        offvalue=False,
        command=on_ignore_extensions_changed
    )

    menu_bar.add_cascade(label="Options", menu=options_menu)

    # Add the menu bar to the root window
    root.config(menu=menu_bar)

    # Bind keyboard shortcuts
    root.bind("<Control-o>", lambda event: open_file())
    root.bind("<Control-r>", lambda event: reload_file())

    # Create a PanedWindow to split the left (tree) and right (pie chart) sections
    paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # Left pane: Treeview widget for folder structure
    left_pane = ttk.Frame(paned_window)
    
    global TREE
    TREE = ttk.Treeview(left_pane)
    TREE.heading("#0", text=PROJECT_NAME, anchor="w", command=lambda: on_tree_heading_click())
    TREE.pack(fill=tk.BOTH, expand=True)
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
    text_widget.pack(fill=tk.BOTH, expand=True)

    # Load styles config from JSON
    global LANGUAGE_STYLES

    with open(local_resource_path("styles.json"), "r", encoding="utf-8") as f:
        LANGUAGE_STYLES = json.load(f)

    def show_content(ax, path=""):
        if not FILES: # No file loaded
            ax.clear()

            ax.text(0.5, 0.5, "No GameMaker Studio 2 Project loaded yet!", ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')

            canvas.draw()

            chart_frame.lift()
        else:
            d = FILES
            
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
            path.append(TREE.item(item_id, 'text'))
            item_id = TREE.parent(item_id)
        return "/".join(reversed(path))  # Reverse the list to get root to leaf order

    def on_tree_heading_click():
        show_content(ax)

    def on_item_selected(event):
        if not TREE.selection():
            return  # No item selected, do nothing

        # Get the selected item
        selected_item = TREE.selection()[0]  # Get the first (and only) item from the selection
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
    TREE.bind("<<TreeviewSelect>>", on_item_selected)

    show_content(ax)

    # Start the Tkinter main event loop
    root.mainloop()

if __name__ == "__main__":
    print("Launch gms2_stats.py, not this file.")
    exit()

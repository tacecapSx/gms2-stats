import os
import json
import re
import sys

class GMFile:
    def __init__(self, content, line_count):
        self.content = "".join([l.replace("\t", "    ") for l in content])
        self.line_count = line_count
    
    def __repr__(self):
        return f"GMFile({self.content}..., {self.line_count})"

class LoadResult:
    def __init__(self, info=None, error=None):
        self.info = info
        self.error = error
    
    def ok(self):
        return self.error is None

def local_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        # Running as a bundled exe
        exe = sys.executable
    else:
        # Running in dev mode
        exe = os.path.abspath(__file__)
    return os.path.join(os.path.dirname(exe), relative_path)

def load(filename):
    def remove_trailing_commas(json_str):
        # This regex will match trailing commas in dictionaries and lists
        json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
        return json_str
    
    def get_asset_path(dirpath, filenames):
        for f in filenames:
            if f.endswith(".yy"):
                with open(os.path.join(dirpath, f), 'r') as yy:
                    json_data = json.loads(remove_trailing_commas(yy.read()))

        path = json_data["parent"]["path"][:-3].split("/")[2:]

        return path

    def update(files, path, value):
        dict_state = files

        for k in path[:len(path)-1]:
            if not k in dict_state:
                dict_state[k] = {}
            dict_state = dict_state[k]
        
        dict_state[path[-1]] = value
    
    def get_event_name(name):
        event_names = {
            "Create_0": "Create",
            "Step_0": "Step",
            "Step_1": "Begin Step",
            "Step_2": "End Step",
            "Draw_0": "Draw",
            "Destroy_0": "Destroy"
        }

        if not name in event_names:
                return name.replace("_", " ")
        
        return event_names[name]

    files = {
        "Scripts": {},
        "Objects": {},
        "Creation Code": {},
        "Shaders": {}
    }

    project_dir = os.path.dirname(os.path.abspath(filename))

    # Load resources
    resources = set()

    resource_dirs = [
        "sprites",
        "sounds",
        "objects",
        "tilesets",
        "fonts",
        "rooms",
        "shaders",
        "particles"
    ]

    for r in resource_dirs:
        p = os.path.join(project_dir, r)
        if os.path.exists(p):
            resources.update(os.listdir(p))

    # Rooms
    roomdir = os.path.join(project_dir, 'rooms')

    for roomname in os.listdir(roomdir):
        with open(f"{os.path.join(os.path.join(roomdir, roomname), roomname)}.yy", 'r') as f:
            j = json.loads(remove_trailing_commas(f.read()))

            for inst in j["instanceCreationOrder"]:
                resources.add(inst["name"])

    # Load scripts
    scripts = set()

    scripts.update(os.listdir(os.path.join(project_dir, "scripts")))

    # Other info
    enum_names = []
    enum_entries = []
    macros = []
    globalvars = []

    def store_content_syntax(content):
        enum_names.extend(re.findall(r'\benum\s+([a-zA-Z_][a-zA-Z0-9_]*)', content))
        macros.extend(re.findall(r'(?<!\w)#macro\s+([a-zA-Z_][a-zA-Z0-9_]*)', content))
        globalvars.extend(re.findall(r'\bglobalvar\s+([a-zA-Z_][a-zA-Z0-9_]*)', content))

        # Enum entries
        matches = re.findall(r'enum\s+\w+\s*{([^}]*)}', content, flags=re.DOTALL)

        for enum_body in matches:
            # Split by comma first to get entries
            raw_entries = enum_body.split(',')

            enum_values = []
            for entry in raw_entries:
                # Remove comments (anything after //)
                entry = re.sub(r'//.*', '', entry)
                # Remove inline assignments (= ...)
                entry = re.sub(r'=.*', '', entry)
                # Strip whitespace
                entry = entry.strip()
                if entry:
                    enum_values.append(entry)
            
            enum_entries.extend(enum_values)

    # Load code
    for dirpath, dirnames, filenames in os.walk(project_dir):
        for f in filenames:
            if f.endswith(".gml") or f.endswith(".vsh") or f.endswith(".fsh"):
                full_path = os.path.join(dirpath, f)
                asset_path = get_asset_path(dirpath, filenames)
                
                with open(full_path, 'r') as fp:
                    content = fp.readlines()
                    line_count = len(content)
                    this_file = GMFile(content, line_count)

                    file_name = os.path.splitext(os.path.basename(f))[0]
                    file_owner = os.path.basename(dirpath)

                    store_content_syntax(this_file.content)

                if "\\objects\\" in dirpath:
                    update(files, ["Objects"] + asset_path + [file_owner, get_event_name(file_name)], this_file)
                elif "\\scripts\\" in dirpath:
                    update(files, ["Scripts"] + asset_path + [file_name], this_file)
                elif "\\rooms\\" in dirpath:
                    update(files, ["Creation Code"] + [file_owner, "_".join(file_name.split("_")[1::])], this_file)
                elif "\\shaders\\" in dirpath:
                    update(files, ["Shaders"] + asset_path + [file_owner, "Vertex" if f.endswith(".vsh") else "Fragment"], this_file)
    
    return (files, list(resources), list(scripts), enum_names, enum_entries, macros, globalvars)

def load_file(filename) -> LoadResult:
    if os.path.exists(filename):
        if not filename.endswith(".yyp"):
            return LoadResult(error="Not a GameMaker Studio 2 Project file (.yyp)")

        project_name = os.path.splitext(os.path.basename(filename))[0]
        
        try:
            load_info = load(filename)

            return LoadResult(info=(project_name, *load_info))
        except:
            return LoadResult(error="Error reading GameMaker Studio 2 Project information. Not a valid project?")
    else:
        return LoadResult(error=f'Path "{filename}" is not a valid GameMaker 2 project file.')

if __name__ == "__main__":
    print("Launch gms2_stats.py, not this file.")
    exit()
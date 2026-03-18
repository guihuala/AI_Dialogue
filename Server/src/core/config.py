import os

# Base directory for the Server (AI_Dialogue/Server)
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Root directory for all data (can be overridden by environment variable for server deployment)
# Default is the 'data' folder in the Server directory
DATA_ROOT = os.getenv("DATA_ROOT_DIR", os.path.join(SERVER_DIR, "data"))

# Common data paths
SAVES_DIR = os.path.join(DATA_ROOT, "saves")
CHROMA_DB_PATH = os.path.join(DATA_ROOT, "chroma_db")
PROMPTS_DIR = os.path.join(DATA_ROOT, "prompts")
CHARACTERS_DIR = os.path.join(PROMPTS_DIR, "characters")
ROSTER_PATH = os.path.join(CHARACTERS_DIR, "roster.json")
EVENTS_DIR = os.path.join(DATA_ROOT, "events")
MODS_DIR = os.path.join(DATA_ROOT, "mods")
PROFILE_PATH = os.path.join(DATA_ROOT, "profile.json")

# Ensure critical directories exist
def ensure_dirs():
    for d in [SAVES_DIR, CHROMA_DB_PATH, CHARACTERS_DIR, MODS_DIR, EVENTS_DIR]:
        os.makedirs(d, exist_ok=True)

ensure_dirs()

# Default Mod (Fallback)
DEFAULT_PROMPTS_DIR = PROMPTS_DIR
DEFAULT_EVENTS_DIR = EVENTS_DIR

# Multi-user data isolation support
def get_user_data_root(user_id: str = "default"):
    """Returns a path like DATA_ROOT/users/{user_id}"""
    path = os.path.join(DATA_ROOT, "users", user_id)
    os.makedirs(path, exist_ok=True)
    return path

def get_user_saves_dir(user_id: str = "default"):
    """User-specific saves directory"""
    if user_id == "default":
        return SAVES_DIR
    path = os.path.join(get_user_data_root(user_id), "saves")
    os.makedirs(path, exist_ok=True)
    return path

def get_user_chroma_path(user_id: str = "default"):
    """User-specific ChromaDB path"""
    if user_id == "default":
        return CHROMA_DB_PATH
    path = os.path.join(get_user_data_root(user_id), "chroma_db")
    os.makedirs(path, exist_ok=True)
    return path

def get_user_prompts_dir(user_id: str = "default"):
    """User-specific active prompts directory"""
    if user_id == "default":
        return DEFAULT_PROMPTS_DIR
    path = os.path.join(get_user_data_root(user_id), "prompts")
    os.makedirs(path, exist_ok=True)
    return path

def get_user_events_dir(user_id: str = "default"):
    """User-specific active events directory"""
    if user_id == "default":
        return DEFAULT_EVENTS_DIR
    path = os.path.join(get_user_data_root(user_id), "events")
    os.makedirs(path, exist_ok=True)
    return path

def get_user_library_dir(user_id: str = "default"):
    """User-specific mod library directory (mod packages)"""
    if user_id == "default":
        return os.path.join(DATA_ROOT, "workshop") # Default shared workshop
    path = os.path.join(get_user_data_root(user_id), "library")
    os.makedirs(path, exist_ok=True)
    return path

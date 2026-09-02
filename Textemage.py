import os
import sys
import runpy

current_dir = os.path.dirname(os.path.abspath(__file__))
sub_script = os.path.join(current_dir, "Hackathon_idea-main", "Textemage.py")

if __name__ == "__main__":
    if os.path.exists(sub_script):
        os.chdir(os.path.dirname(sub_script))
        runpy.run_path(sub_script, run_name="__main__")
    else:
        print(f"Error: Could not find {sub_script}")

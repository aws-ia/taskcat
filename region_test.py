from pathlib import Path
from taskcat._cli_modules.update_ami import UpdateAMI
proot = Path("/Users/andglenn/development/quickstarts/mine/ribbon-sbc/")

U = UpdateAMI(project_root=proot)

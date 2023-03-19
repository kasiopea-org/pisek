import subprocess
from . import util

def feed(args, command, input=""):
    if args.ssh_destination is not None:
        cmd = ["ssh", args.ssh_destination, command]
    else:
        print(command, type(command))
        cmd = ["bash",  "-c", command]
    return subprocess.run(cmd, stdout=subprocess.PIPE, input=input.encode("utf-8")).stdout.decode('utf-8').strip()

def copy_tmp_file_and(args, command, contents=None, basename=None):
    assert contents is not None
    assert basename is not None
    return feed(args, f'tmp=$(mktemp -d pisek-XXXXXXXXXXXX); cd $tmp; cat > {basename}; {command}; cd ../; rm -rf $tmp', contents)

# Blender Support

This directory contains Blender helper add-ons that are maintained with the
Holodeck project.

## NLA Frame Tools

Canonical file:

```text
/Users/james_bellenger/workspace/holodeck/blender-support/nla_frame_tools.py
```

To make Blender load this canonical copy directly, replace the installed add-on
file with a symlink:

```sh
ln -sf /Users/james_bellenger/workspace/holodeck/blender-support/nla_frame_tools.py \
  "$HOME/Library/Application Support/Blender/5.1/scripts/addons/nla_frame_tools.py"
```

After changing the symlink target, restart Blender or disable and re-enable the
add-on from Preferences.

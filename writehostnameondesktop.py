from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import truetype
import os
import shutil
import subprocess
user = 'student'

with open(f'/home/{user}/.config/plasma-org.kde.plasma.desktop-appletsrc', 'r') as inp:
    for i in inp.readlines():
        if i.startswith('Image'):
            line = i
            break
fname = line.split('//')[1].rstrip()
os.system(f'mkdir -p /home/{user}/.desktop_wallpapers')
shutil.copyfile(fname, f"/home/{user}/.desktop_wallpapers/{fname.split('/')[-1]}")
fname = f"/home/{user}/.desktop_wallpapers/{fname.split('/')[-1]}"
pos = fname.rindex('.')
fname2 = fname[:pos] + '_with_host' + fname[pos:]
shutil.copyfile(fname, fname2)
img = Image.open(fname2)
draw = ImageDraw.Draw(img)
width, height = img.size
text = subprocess.check_output('hostname').decode('utf-8').strip()
fontsize = 10
font = truetype('/usr/share/fonts/ttf/gnu-free/FreeMono.ttf', fontsize)
while draw.textlength(text, font) < width // 3:
    fontsize += 1
    font = ImageFont.truetype('/usr/share/fonts/ttf/gnu-free/FreeMono.ttf', fontsize)
textwidth = draw.textlength(text, font)
margin = width // 10
x = width // 2 - textwidth // 2 - margin
y = height - textwidth // 5 - margin
draw.text((x, y), text, (0, 0, 0), font=font)
img.save(fname2)

settingsfilename = f'/home/{user}/.config/plasma-org.kde.plasma.desktop-appletsrc'
shutil.copyfile(settingsfilename, settingsfilename + '.bak')
with open(settingsfilename, 'r') as inp:
    lines = inp.readlines()
for i in range(len(lines)):
    if lines[i] == line:
        lines[i] = line.split('//')[0] + '//' + fname2
        break
with open(settingsfilename, 'w') as out:
    print(*lines, sep='', file=out)

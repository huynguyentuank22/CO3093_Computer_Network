from bcoding import bencode, bdecode
import time 
file_path = r'C:\Users\Huy\Documents\Tuan_Huy\CO3093_Computer_Network\pdf-sample.pdf'
torrent_path = r'C:\Users\Huy\Documents\Tuan_Huy\CO3093_Computer_Network\drake.torrent'

with open(torrent_path, 'rb') as file:
    contents = bdecode(file)
with open('torrent.txt', 'w', encoding='utf-8') as file:
    for key, value in contents.items():
        file.write(f'{str(key)}: {str(value)}\n')
        file.write('\n')

if 'announce-list' in contents:
    announce_list = [x for x in contents['announce-list']]
else:
    announce_list = [contents['announce']]
# print(announce_list)
multipleFiles = False
if 'files' in contents['info']:
    multipleFiles = True

print(multipleFiles)

print(str(time.time()))

PLUGIN_ID = 'server_updater'
PLUGIN_METADATA = {
    'id': PLUGIN_ID,
    'version': '0.1.0',
    'name': 'Server Updater',
    'description': '自动检查并获取服务端更新',
    'author': 'Ra1ny_Yuki',
    'link': 'https://github.com/Lazy-Bing-Server/Server-Updater',
    'dependencies': {
        'mcdreforged': '>=1.5.0'
    }
}

from mcdreforged.api.all import *
import json
import os
import re
from datetime import datetime

config_file = 'config.json'
log_file = 'update_log.log'
prefix = '!!update'

default_config = {

}
config = {}

def show_help(source: CommandSource):
    help_message = f'''---- MCDR {PLUGIN_METADATA['name']} v{PLUGIN_METADATA['version']} ----
{PLUGIN_METADATA['description']}
§7{prefix} §r显示此帮助信息
§7{prefix} reload§r 重载此插件
§7{prefix} check§r 检查更新并下载
§7{prefix} status§r 显示当前版本和更新信息
§7{prefix} enable§r 启用自动更新
§7{prefix} disable§r 禁用自动更新
§7{prefix} set§r 设定每日自动检查更新时间
§7{prefix} now§r 立即更新
'''.strip()
    help_msg_rtext = RTextList()
    for line in help_message.splitlines():
        result = re.search(r'(?<=§7){}[\S ]*?(?=§)'.format(prefix), line)
        if result is not None:
            cmd = result.group() + ' '
            help_msg_rtext.append(RText(line).c(RAction.suggest_command, cmd).h('点击以填入 §7{}§r'.format(cmd)))
        else:
            help_msg_rtext.append(line)
	source.reply(help_msg_rtext)

def output_log(msg: str):
    msg = msg.replace('§r', '').replace('§d', '').replace('§c', '').replace('§6', '').replace('§e', '').replace('§a', '')
    with open(os.path.join(log_path), 'a+') as log:
        log.write(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + msg + '\n')
    print("[MCDR] " + datetime.now().strftime("[%H:%M:%S]") + ' [{}/\033[1;32mINFO\033[0m] '.format(PLUGIN_METADATA['id']) + msg)

def get_config():
    global config
    if not os.path.isdir(data_folder):
        os.makedirs(data_folder)
    if not os.path.isfile(config_path):
        with open(config_path, 'w', encoding = 'UTF-8') as file:
            json.dump(default_config, file, indent = 2)
    with open(config_path, 'r', encoding = 'UTF-8') as file:
        content = json.load(file)
    need_update = False
    for key, value in default_config.keys():
        try:
            content[key]
        except:
            content[key] = value
            need_update = True
    if need_update:
        with open(config_file, 'w', encoding = 'UTF-8') as file:
            json.dump(content, file)
    config.update(content)
         
def write_config(key: str, value = None):
    with open(config_path, 'r', encoding = 'UTF-8') as f:
        content = json.load(f)
    if value is not None:
        content[key] = value
    else:
        content[key] = default_config.get(key)
    config.update(content)
    with open(config_path, 'w+', encoding = 'UTF-8'):
        json.dump(content)

def on_load(server: ServerInterface, prev_module):
    get_path(server)
    get_config()
    register_stuffs(server)

def register_stuffs(server: ServerInterface):
    server.register_command()
    server.register_help_message(prefix, '服务端自动更新管理')

def get_path(server: ServerInterface):
    global data_folder, config_path, log_path
    data_folder = server.get_data_folder()
    config_path = os.path.join(data_folder, config_file)
    log_path = os.path.join(data_folder, log_file)

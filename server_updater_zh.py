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

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from urllib.request import urlopen, urlretrieve
from mcdreforged.api.all import *
from zipfile import ZipFile
from threading import Lock
from parse import parse
from ruamel import yaml
import datetime
import hashlib
import shutil
import json
import os
import re

config_file = 'config.yml'
log_file = 'update_log.log'
prefix = '!!update'

default_config = {
    'enableAutoUpdate': False,
    'autoUpdateTime': '04:00:00',
    'checkSnapshot': False,
    'checkInterval': 30,
    'permission': {
        'reload': 2,
        'status': 1,
        'enable': 2,
        'disable': 2,
        'now': 2,
        'rule': 2
    },
}
rule_description = {
    'enableAutoUpdate': ['启用自动更新', 'bool'],
    'autoUpdateTime': ['每日自动检查更新时间', 'time'],
    'checkSnapshot': ['是否检查快照版本更新', 'bool'],
    'checkInterval': ['自动检查更新时有人的再次重试时间/min', 'int']
    }
config = {}
general_lock = Lock()
update_lock = Lock()
required = False
bool_limit = {'true': True, 'True': True, 'false': False, 'False': False}

class pendingUpdate:
    def __init__(self):
        self.snapshot = config['checkSnapshot']
        self.refresh_latest()

    def is_outdated(self, snapshot = False):        
        self.refresh_latest()
        target_version = self.latest_release
        if snapshot:
            target_version = self.latest_snapshot
        if config != target_version:
            return target_version
        return False

    def refresh_latest(self):
        js = access_api('https://launchermeta.mojang.com/mc/game/version_manifest.json')
        self.latest_snapshot = js['latest']['snapshot']
        self.latest_release = js['latest']['release']
        return self
    
    def status(self):
        current_version = get_server_version()
        return current_version, self.latest_release, self.latest_snapshot
        
class getServerJSON:
    def __init__(self, server_file: ZipFile):
        self.pkg = server_file
    def __enter__(self):
        self.pkg.extract('version.json', data_folder)
    def __exit__(self, type, value, stack_info):
        os.remove(os.path.join(data_folder, 'version.json'))

def print_message(source: CommandSource, msg, tell = True, prefix = '[ServerUpdater] '):
	msg = prefix + msg
	if source.is_player and not tell:
		source.get_server().say(msg)
	else:
		source.reply(msg)

def rclick(message: str, hover_text: str, click_content: str, click_event = RAction.run_command):
    return RText(message).set_hover_text(hover_text).set_click_event(click_event, click_content)

def access_api(url):
    return json.loads(urlopen(url).read().decode('utf8'))

def show_help(source: CommandSource):
    help_message = f'''---- MCDR {PLUGIN_METADATA['name']} v{PLUGIN_METADATA['version']} ----
{PLUGIN_METADATA['description']}
§7{prefix} §r显示此帮助信息
§7{prefix} reload§r 重载此插件
§7{prefix} status§r 显示当前版本和更新信息
§7{prefix} enable§r 启用自动更新
§7{prefix} disable§r 禁用自动更新
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
        if line != help_message.splitlines()[-1]:
            help_msg_rtext.append('\n')
    source.reply(help_msg_rtext)

def output_log(msg: str):
    msg = msg.replace('§r', '').replace('§d', '').replace('§c', '').replace('§6', '').replace('§e', '').replace('§a', '')
    with open(os.path.join(log_path), 'a+') as log:
        log.write(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + msg + '\n')
    print("[MCDR] " + datetime.datetime.now().strftime("[%H:%M:%S]") + ' [{}/\033[1;32mINFO\033[0m] '.format(PLUGIN_METADATA['id']) + msg)

def get_source_name(source: CommandSource):
    if source.is_player:
        return source.player
    else:
        return '#Console'

def get_config():
    global config
    if not os.path.isdir(data_folder):
        os.makedirs(data_folder)
    if not os.path.isfile(config_path):
        with open(config_path, 'w', encoding = 'UTF-8') as file:
            yaml.round_trip_dump(default_config, file, allow_unicode = True, encoding = 'UTF-8')
    with open(config_path, 'r', encoding = 'UTF-8') as file:
        content = yaml.round_trip_load(file)

    need_update_keylist = list()
    for key, value in default_config.items():
        try:
            if content.get(key) == None:
                content[key] = value
                need_update_keylist.append(key)
        except:
            need_update_keylist[0] = 'rua'
            content = default_config
            
    if len(need_update_keylist) > 0:
        if need_update_keylist[0] != 'rua':
            output_log('Using default value for missing keys: ' + str(need_update_keylist).strip('[]'))
        else:            
            output_log('Error decoding config file, using default')
        with open(config_file, 'w', encoding = 'UTF-8') as file:
            yaml.round_trip_dump(content, file, allow_unicode = True, encoding = 'UTF-8')
    config.update(content)
         
def write_config(key: str, value = None):
    with open(config_path, 'r', encoding = 'UTF-8') as f:
        content = yaml.round_trip_load(f)
    if value is not None:
        content[key] = value
    else:
        content[key] = default_config.get(key)
    config.update(content)
    with open(config_path, 'w+', encoding = 'UTF-8') as f:
        yaml.round_trip_dump(config, f, allow_unicode = True, encoding = 'UTF-8')

def replace_server(target_version: str):
    current_version = get_server_version()
    backup_path = os.path.join(backup_folder, current_version + '.jar')
    shutil.move(server_path, backup_path)
    target_path = os.path.join(backup_folder, target_version + '.jar')
    shutil.move(target_path, server_path)

@new_thread(PLUGIN_ID)   
def download_server(version: str, loop = 0):
    try:
        general_lock.acquire(blocking = False)
    except:
        pass
    if os.path.isdir(backup_folder):
        os.makedirs(backup_folder)
    target_path = os.path.join(backup_folder, version + '.jar')
    if os.path.isfile(target_path):
        os.remove()
    js = access_api('https://launchermeta.mojang.com/mc/game/version_manifest.json')
    for version_info in js['versions']:
        if version_info['id'] == version:
            verion_js = access_api(version_info['url'])
            break
    urlretrieve(verion_js['downloads']['server']['url'], target_path)
    if not sha1_check(target_path, verion_js['downloads']['server']['sha1']):
        if loop > 3:
            output_log('Hash check failed for {} too much times!'.format(version + '.jar'))
            os.remove(target_path)
        else:
            output_log('Hash check failed for {}. Retrying...')
            loop += 1
            download_server(version, loop)
    else:
        output_log('Download {} server successfully')
    general_lock.release()

def sha1_check(file: str, hash: str):
    sha1 = hashlib.sha1()
    with open(file, 'rb') as f:
        sha1.update(f.read())
    return sha1.hexdigest() == hash

def get_server_version():
    server_file = ZipFile(server_path)
    with getServerJSON(server_file):
        with open(os.path.join(data_folder, 'version.json'), 'r', encoding = 'UTF-8') as f:
            version = json.load(f)['id']
    return version

def rule_info(rule: str, value = None):
    old_value = config[rule]
    current_value = old_value
    if value:
        current_value = value
    content = RText(str(current_value), RColor.yellow, RStyle.bold)
    if value:
        content += RText(str(old_value), RColor.red, RStyle.strikethrough).set_click_event(RAction.run_command, f'{prefix} {rule} {old_value}').set_hover_text('点击此处撤销更改')    
    return RText(f'{rule_description[rule][0]}({rule})').set_hover_text('点此补全命令').set_click_event(RAction.suggest_command, f'{prefix} {rule} ') + '\n当前值: ' + content + ' 默认值: ' + RText(default_config[rule], RColor.gray, RStyle.underlined).set_click_event(RAction.run_command, f'{prefix} {rule} {default_config[rule]}').set_hover_text('点击此处应用默认值')
    
@new_thread(PLUGIN_ID)
def reload_config(source: CommandSource):
    get_config()
    global update
    update = pendingUpdate()
    print_message(source, '重载配置文件完成')

@new_thread(PLUGIN_ID)
def check_status(source: CommandSource):
    current, release, snapshot = update.status()
    listtext = RTextList()
    listtext.append(f'''§l服务端版本信息如下: §r
§a当前服务端版本§r: {current}
§e最新正式版§r: {release}
§c最新快照版§r: {snapshot}
§l可配置项如下:§r ''')
    for rule in rule_description.keys():
        listtext.append('\n' + rule_info(rule))
    print_message(source, listtext)

@new_thread(PLUGIN_ID)
def enable_auto():
    if not sched.running:
        sched.resume()

@new_thread(PLUGIN_ID)
def disable_auto():
    if sched.running:
        sched.pause()

@new_thread(PLUGIN_ID)
def auto_check(server: ServerInterface):
    server.say(f'[ServerUpdater] 正在自动检查服务端版本更新(每日§e{config["autoUpdateTime"]}§r)')
    target_version = update.refresh_latest().is_outdated()
    if target_version and not update_lock.locked():
        if not os.path.isfile(server_path):
            server.say(f'检查到有新版本{target_version}, 正在下载, 请放心, 本插件不会在玩家未下线时进行更新')
            download_server(target_version)
            general_lock.acquire(blocking = True)
            general_lock.release()
            if not os.path.isfile(server_path):
                server.say('文件多次完整性校验失败, 自动更新中止')
            else:
                server.say('文件下载完成, 即将开始更新')
                _excute_update()
        else:
            server.say(f'检查到有新版本{target_version}(已下载), 即将重启执行更新任务')
            _excute_update()
    elif not target_version and update_lock.locked():
        server.say('已有正在执行的更新任务了, 自动更新中止')
    else:
        server.say('当前服务端为最新')

def _excute_update(server: ServerInterface, target_version: str, first_try = True):
    empty = not is_player_in(server)
    if empty:
        excute_update(server, target_version)
    elif not empty and first_try:
        server.say(f'仍有未下线的玩家, 任务已暂停, §e{config["retryInterval"]}§r分钟后再次尝试')
        interval_trigger = IntervalTrigger(seconds = int(60 * config['retryInterval']))
        sched.add_job(_excute_update, interval_trigger, args = (server, target_version, False), id = 'wait')
    else:
        server.say(f'仍有未下线的玩家, 任务已中止')
    if not first_try:
        sched.remove_job('wait')
        
def is_player_in(server: ServerInterface):
    return parse(server.rcon_query('list'), 'There are {number} of a max of {} players online: {}')['number'] != '0'

@new_thread(PLUGIN_ID)
def update_now(source: CommandSource):
    global required
    if required:
        print_message(source, '已请求更新了, 请勿重复请求')
        return
    if update_lock.locked():
        print_message(source, '已经在进行更新操作了, 请勿重复请求')
        return
    required = True
    print_message(source, rclick('使用§7{0} confirm§r 确认§c更新§r '.format(prefix), '点此确认立即更新', f'!!{prefix} confirm') + rclick(',使用§7{0} abort§r 取消'.format(prefix), '点击取消', '{0} abort'.format(prefix)))

@new_thread(PLUGIN_ID)
def confirm_update(source: CommandSource, confirm = True):
    global required
    if not required:
        print_message(source, '没有需要确认的请求')
    elif update_lock.locked():
        print_message(source, '已经在进行更新操作了, 请勿重复请求')
    elif confirm == False:
        required = False
        print_message(source, '已取消更新请求')
    else:
        required = False
        print_message(source, '即将开始更新, 请勿关闭服务端', tell = False)
        _update_now(source)

@new_thread(PLUGIN_ID)
def _update_now(source: CommandSource):
    server = source.get_server()
    update_lock.acquire(blocking = True)
    target_version = update.refresh_latest().is_outdated()
    if not target_version:
        server.say('当前版本已是最新版')
        return
    target_file = os.path.join(backup_folder, target_version + '.jar')
    if not os.path.isfile(target_file):
        download_server(target_version)
        general_lock.acquire(blocking = True)
        general_lock.release()
        server.say('下载更新成功, 将开始更新')
    else:
        server.say('该版本服务端已下载, 将直接开始更新')
    output_log(f'{get_source_name(source)} started server update manually. Target version: {target_version}')
    excute_update(source, target_version)
    update_lock.release()
    
def excute_update(server: ServerInterface, target_version):
    num = 5
    while num > 0:
        num -= 1
        server.say(f'§c{num}秒将重启服务端执行更新任务§r')
    server.stop()
    output_log('Waiting for server stop!')
    server.wait_for_start()
    replace_server(target_version)
    output_log('Replaced server file. Restarting...')
    server.start()

@new_thread(PLUGIN_ID)
def cmd_error(source: CommandSource):
    print_message(source, rclick('§c指令错误§r, 点此获取帮助信息', '获取帮助信息', prefix))
    
@new_thread(PLUGIN_ID)
def change_rule(source: CommandSource, rule: str, value = None):
    if not rule in rule_description.keys():
        cmd_error(source)
    elif value is None:
        print_message(source, rule_info(rule))
    else:
        lvl = config['permission']['rule']
        if lvl > source.get_permission_level():
            print_message(source, f'§c权限不足, 你想桃子呢, 需要权限等级{lvl}§r')
            return
        invalid_value = False
        if rule_description[rule][1] == 'bool':
            if not value in bool_limit.keys():
                invalid_value = True
            else:
                value_converted = bool_limit[value]
        elif rule_description[rule][1] == 'time':
            time_list = value.split(':')
            for item in time_list:
                try:
                    int(item)
                except:
                    invalid_value = True
            if len(time_list) != 3:
                invalid_value = True
            value_converted = value
        else:
            try:
                value_converted = int(value)
            except:
                invalid_value = True
        if invalid_value:
            print_message(source, f'§c无效数值: §m{value}§r')
            return
        print_message(source, rule_info(rule, value_converted))
        write_config(rule, value_converted)
        output_log(f'{get_source_name(source)} set rule {rule} to {value}')
        if rule == 'enableAutoUpdate':
            try:
                if value_converted:
                    sched.resume()
                else:
                    sched.pause()
            except:
                pass
        elif rule == 'autoUpdateTime':
            set_scheduler(source.get_server(), set)

def set_scheduler(server: ServerInterface, set = False):
    running = sched.running
    if running:
        sched.pause()
    sched.remove_all_jobs()
    if set:
        hrs, mins, secs = config["autoUpdateTime"].split(':')
        sched.add_job(auto_check, 
        'cron', 
        args = [server], 
        id = 'regular', 
        hour = int(hrs), minute = int(mins), second = int(secs))
    if running:
        sched.resume()

def init_scheduler(server: ServerInterface):
    global sched
    sched = BackgroundScheduler()
    set_scheduler(server, True)
    sched.start()
    if not config['enableAutoUpdate']:
        sched.pause()    

def register_stuffs(server: ServerInterface):
    def permed_literal(literal):   
        lvl = config['permission'].get(literal, 0)
        return Literal(literal).requires(lambda src: src.has_permission(lvl), failure_message_getter = lambda: f'§f[ServerUpdater] §c权限不足, 你想桃子呢, 需要权限等级{lvl}')

    server.register_command(
        Literal(prefix).runs(show_help).on_child_error(UnknownArgument, lambda src: cmd_error(src), handled = True).
        then(permed_literal('reload').runs(lambda src: reload_config(src))).
        then(permed_literal('status').runs(lambda src: check_status(src))).
        then(permed_literal('now').runs(lambda src: update_now(src))).
        then(permed_literal('confirm').runs(lambda src: confirm_update(src))).
        then(permed_literal('abort').runs(lambda src: confirm_update(src, False))).
        then(QuotableText('rule').runs(lambda src, ctx: change_rule(src, ctx['rule'])).
            then(QuotableText('value').runs(lambda src, ctx: change_rule(src, ctx['rule'], ctx['value'])))))
    server.register_help_message(prefix, '服务端自动更新管理')

def get_path(server: ServerInterface):
    global data_folder, config_path, log_path, server_path, backup_folder
    data_folder = server.get_data_folder()
    config_path = os.path.join(data_folder, config_file)
    log_path = os.path.join(data_folder, log_file)
    with open('config.yml', 'r', encoding = 'UTF-8') as f:
        content = yaml.round_trip_load(f)
    server_folder = content['working_directory']
    server_file = content['start_command'].split(' ')[content['start_command'].split(' ').index('-jar') + 1]
    server_path = os.path.join(server_folder, server_file)
    backup_folder = os.path.join(data_folder, 'servers')

def on_load(server: ServerInterface, prev_module):
    get_path(server)
    get_config()
    global update
    update = pendingUpdate()
    init_scheduler(server)
    register_stuffs(server)

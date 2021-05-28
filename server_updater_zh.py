PLUGIN_ID = 'server_updater'
PLUGIN_METADATA = {
    'id': PLUGIN_ID,
    'version': '1.0.1',
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
import time
import os
import re

# 可配置项开始
config_file = 'config.yml'
log_file = 'update_log.log'
backup_dir = 'servers'
prefix = '!!update'
# 可配置项结束, 非此范围内的东西, 除非你知道你在干嘛, 勿动

default_config = {
    'enableAutoUpdate': False,
    'autoUpdateTime': '04:00:00',
    'checkSnapshot': False,
    'forceAutoUpdate': False,
    'playerInterruptRetryInterval': 30,
    'playerInterruptRetryTimes': 1,
    'hashFailRetryTimes': 0,
    'serverPath': 'default',
    'verbose': False,
    'permission': {
        'reload': 2,
        'status': 1,
        'enable': 2,
        'disable': 2,
        'now': 2,
        'rule': 2
    }}
rule_description = {
    'enableAutoUpdate': ['启用自动更新', 'bool'],
    'forceAutoUpdate': ['自动更新时不检查是否有玩家在线', 'bool'],
    'autoUpdateTime': ['每日自动检查更新时间', 'time'],
    'checkSnapshot': ['是否检查快照版本更新', 'bool'],
    'playerInterruptRetryTimes': ['服务器非空时更新重试次数§r(§4>0§f)', 'int'],
    'playerInterruptRetryInterval': ['服务器非空时更新重试间隔§r/分钟', 'int'],
    'hashFailRetryTimes': ['下载服务端哈希校验失败重试次数§r(§4>0§f)', 'int']}
config = {}
general_lock = Lock()
update_lock = Lock()
sched = None
required = False
bool_limit = {'true': True, 'false': False}

class pendingUpdate:
    def __init__(self):
        self.snapshot = config['checkSnapshot']

    def is_outdated(self):        
        self.refresh_latest()
        current_version = get_server_version()
        target_version = self.latest_release
        if config['checkSnapshot']:
            target_version = self.latest_snapshot
        debug_log(f'target: {target_version} current: {current_version}')
        if current_version != target_version and current_version != 'N/A':
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

@new_thread(PLUGIN_ID)
def cmd_error(source: CommandSource):
    print_message(source, rclick('§c指令错误§r, 点此获取帮助信息', '获取帮助信息', prefix))

@new_thread(PLUGIN_ID)
def show_help(source: CommandSource):
    help_message = f'''---- MCDR {PLUGIN_METADATA['name']} v{PLUGIN_METADATA['version']} ----
{PLUGIN_METADATA['description']}
§7{prefix} §r显示此帮助信息
§7{prefix} reload§r 重载此插件
§7{prefix} status§r 显示当前版本更新信息和插件配置项
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

def debug_log(msg: str):
    if config['verbose']:
        msg = msg.replace('§r', '').replace('§d', '').replace('§c', '').replace('§6', '').replace('§e', '').replace('§a', '')
        with open(os.path.join(log_path), 'a+') as log:
            log.write(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + msg + '\n')
        print("[MCDR] " + datetime.datetime.now().strftime("[%H:%M:%S]") + ' [{}/\033[1;36mDEBUG\033[0m] '.format(PLUGIN_METADATA['id']) + msg)

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
        with open(config_path, 'w', encoding = 'UTF-8') as f:
            yaml.round_trip_dump(default_config, f, allow_unicode = True, encoding = 'UTF-8')
    need_update_keylist = list()
    try:
        with open(config_path, 'r', encoding = 'UTF-8') as f:
            content = yaml.round_trip_load(f)
    except:
        content = default_config.copy()
        need_update_keylist[0] = 'rua'
        output_log('Error decoding config file, using default')

    for key, value in default_config.items():
        if not key in content.keys():
            content[key] = value
            need_update_keylist.append(key)
            
    if len(need_update_keylist) > 0:
        if need_update_keylist[0] != 'rua':
            output_log('Applied default value for missing keys: ' + str(need_update_keylist).strip('[]'))
        with open(config_path, 'w', encoding = 'UTF-8') as f:
            yaml.round_trip_dump(content, f, allow_unicode = True, encoding = 'UTF-8')
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
    if current_version == 'N/A':
        output_log('The file you specified is not a valid vanilla server file. Execution interrupted and restarting...')
        return    
    backup_path = os.path.join(backup_folder, current_version + '.jar')
    shutil.move(server_path, backup_path)
    target_path = os.path.join(backup_folder, target_version + '.jar')
    shutil.move(target_path, server_path)
    output_log('Replaced server file. Restarting...')

@new_thread(PLUGIN_ID)   
def download_server(version: str, loop = 0):
    if loop == 0:
        general_lock.acquire(blocking = False)
    if not os.path.isdir(backup_folder):
        os.makedirs(backup_folder)
    target_path = os.path.join(backup_folder, version + '.jar')
    debug_log('Starting download, file name: ' + target_path)
    if os.path.isfile(target_path):
        os.remove()
    try:
        js = access_api('https://launchermeta.mojang.com/mc/game/version_manifest.json')
        for version_info in js['versions']:
            if version_info['id'] == version:
                verion_js = access_api(version_info['url'])
                break
    except:
        output_log('Exception occured while fetching data from Mojang API. Interrupted.')
        if general_lock.locked() and loop == 0:
            general_lock.release()
        return
    try:
        urlretrieve(verion_js['downloads']['server']['url'], target_path)
    except:
        pass
    if not sha1_check(target_path, verion_js['downloads']['server']['sha1']):
        if loop >= get_integer('hashFailRetryTimes'):
            output_log('Hash check failed for {} too much times!'.format(version + '.jar'))
            os.remove(target_path)
        else:
            output_log('Hash check failed for {}. Retrying...')
            download_server(version, loop + 1)
    else:
        output_log('Download {} server successfully')
    if loop == 0:
        general_lock.release()

def sha1_check(file: str, hash: str):
    try:
        sha1 = hashlib.sha1()
        with open(file, 'rb') as f:
            sha1.update(f.read())
        return sha1.hexdigest() == hash
    except:
        return False

def get_server_version():
    try:
        server_file = ZipFile(server_path)    
        with getServerJSON(server_file):
            with open(os.path.join(data_folder, 'version.json'), 'r', encoding = 'UTF-8') as f:
                version = json.load(f)['id']
        return version
    except:
        return 'N/A'

def rule_info(rule: str, value = None) -> RTextBase:
    server_name = rclick(f'§l{rule_description[rule][0]}§r(§b{rule}§r)', '点此补全命令', f'{prefix} {rule} ', RAction.suggest_command)
    default_value = rclick(f'§7§n{default_config[rule]}§r', '点击此处应用默认值', f'{prefix} {rule} {default_config[rule]}')
    old_value = config[rule]
    current_value = old_value
    if value is not None:
        current_value = value
    content = f'§e§l{str(current_value)}'
    if value is not None:
        content += rclick(f'§c§m{str(old_value)}', '点击此处撤销更改', f'{prefix} {rule} {old_value}')
    return server_name + '\n当前值: ' + content + ' 默认值: ' + default_value
    
@new_thread(PLUGIN_ID)
def reload_config(source: CommandSource):
    get_config()
    global update
    update = pendingUpdate()
    init_scheduler(source.get_server())
    print_message(source, '重载配置文件§a完成§r')

@new_thread(PLUGIN_ID)
def check_status(source: CommandSource):
    current, release, snapshot = update.refresh_latest().status()
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
def auto_check(server: ServerInterface):
    debug_log('Auto checking update...')
    server.say(f'[ServerUpdater] 正在自动检查服务端版本更新(每日§e{config["autoUpdateTime"]}§r)')
    if not config['forceAutoUpdate']:
        server.say('§a请放心, 玩家未下线时不会重启进行更新§r')
    target_version = update.is_outdated()
    if target_version and not update_lock.locked():
        update_lock.acquire()
        if not os.path.isfile(os.path.join(backup_folder, target_version + '.jar')):
            server.say(f'检查到有新版本{target_version}, 正在§e下载§r')
            debug_log('Downloading {}'.format(target_version))
            download_server(target_version)
            general_lock.acquire(blocking = True)
            general_lock.release()
            if not os.path.isfile(server_path):
                server.say('文件多次完整性校验失败, 自动更新§c中止§r')
            else:
                server.say('文件下载完成, 即将开始更新')
                _excute_update(server, target_version)
        else:
            server.say(f'检查到有新版本{target_version}(§e已下载§r)')
            _excute_update(server, target_version)
        update_lock.release()
    elif not target_version and update_lock.locked():
        server.say('已有正在执行的更新任务了, 自动更新§c中止§r')
    else:
        server.say('当前服务端为§a最新§r')

def _excute_update(server: ServerInterface, target_version: str, loop = 0):
    debug_log('Trying to execute update')
    empty = is_server_empty(server)
    if sched.get_job('wait'):
        sched.remove_job('wait')
        sched.resume_job('regular')
    if empty:
        excute_update(server, target_version)
    elif not empty and loop < get_integer('playerInterruptRetryTimes'):
        debug_log('There\'s still player(s) remaining! Update will retry after {} minute(s)'.format(config['playerInterruptRetryInterval']))
        server.say(f'仍有未下线的玩家, 任务已§e暂停§r, §e{config["playerInterruptRetryInterval"]}§r分钟后再次尝试(剩余次数{config["playerInterrruptRetryTimes"] - loop}')
        sched.add_job(_excute_update, 'interval', args = (server, target_version, loop + 1), id = 'wait', seconds = 60*get_integer('playerInterruptRetryInterval', 1))
        sched.pause_job('regular')
    else:
        server.say(f'仍有未下线的玩家, 任务已§c中止§r')
        debug_log('There\'s still player(s) remaining! Update interrupted')
    if not loop <= get_integer('playerInterruptRetryTimes'):
        if sched.get_job('wait'):
            sched.remove_job('wait')
            sched.resume_job('regular')

def get_integer(rule: str, min = 0):
    value = int(config[rule])
    if value < min:
        write_config(rule, min)
        value = get_integer(rule, min)
    return value
        
def is_server_empty(server: ServerInterface):
    if not config['forceAutoUpdate']:
        return_message = server.rcon_query('list').strip()
        server.say('即将§e尝试§r执行更新, 正在检查服务器是否有人(服务器有人时不会进行更新)')
        debug_log(return_message)
        num = parse('There are {number} of a max of {max} players online{etc}' , return_message)['number']
        return num == '0'
    else:
        server.say('即将§c强制§r执行更新, 请注意!!!')
        return True

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
    print_message(source, rclick('使用§7{0} confirm§r 确认§c更新§r '.format(prefix), '点此确认立即更新', f'{prefix} confirm') + rclick(',使用§7{0} abort§r 取消'.format(prefix), '点击取消', '{0} abort'.format(prefix)))

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
        print_message(source, '即将开始更新, §c请勿关闭服务端§r', tell = False)
        if sched.get_job('wait'):
            sched.remove_job('wait')
            sched.resume_job('regular')
        _update_now(source)

@new_thread(PLUGIN_ID)
def _update_now(source: CommandSource):
    server = source.get_server()
    target_version = update.is_outdated()
    if not target_version:
        server.say('§c当前版本已是最新版或查询不到当前服务端版本§r')
        return
    update_lock.acquire(blocking = True)
    target_file = os.path.join(backup_folder, target_version + '.jar')
    if not os.path.isfile(target_file):
        download_server(target_version)
        general_lock.acquire(blocking = True)
        general_lock.release()
        server.say('下载更新§a成功§r, 将开始更新')
    else:
        server.say('该版本服务端§e已下载§r, 将直接开始更新')
    output_log(f'{get_source_name(source)} started server update manually. Target version: {target_version}')
    excute_update(server, target_version)
    update_lock.release()
    
def excute_update(server: ServerInterface, target_version):
    output_log(f'Start updating server to {target_version}')
    num = 5
    while num > 0:
        server.say(f'§c{num}秒后将重启服务端执行更新任务...§r')
        debug_log(f'Restarting: {num}...')
        num -= 1
        time.sleep(1)
    server.stop()
    output_log('Waiting for server stop!')
    server.wait_for_start()
    replace_server(target_version)
    server.start()
    
@new_thread(PLUGIN_ID)
def change_rule(source: CommandSource, rule: str, value = None):
    if not rule in rule_description.keys():
        cmd_error(source)
    elif value is None:
        print_message(source, '查询到下列配置项: \n' + rule_info(rule))
    else:
        lvl = config['permission']['rule']
        if lvl > source.get_permission_level():
            print_message(source, f'§c权限不足, 你想桃子呢, 需要权限等级{lvl}§r')
            return
        value_converted = check_value(rule_description[rule][1], value)
        if value_converted == None:
            print_message(source, f'§c无效数值: §m{value}§r')
            return
        print_message(source, '设置项已更改, 所有计时器均已重置\n' + rule_info(rule, value_converted))
        write_config(rule, value_converted)
        output_log(f'{get_source_name(source)} set rule {rule} to {value}')
        init_scheduler(source.get_server())

def check_value(limit: str, value: str):
    if limit == 'time':
        try:
            time.strptime(value, '%H:%M:%S')
            return value
        except:
            return None
    elif limit == 'bool':
        if value.lower() not in bool_limit.keys():
            return None
        else:
            return bool_limit[value.lower()]
    elif limit == 'int':
        try:
            return int(value)
        except:
            return None

def set_scheduler(server: ServerInterface, set = False):
    running = sched.running
    if running:
        sched.pause()
    sched.remove_all_jobs()
    if set:
        hrs, mins, secs = config["autoUpdateTime"].split(':')
        sched.add_job(auto_check, 'cron', args = [server], id = 'regular', 
        hour = int(hrs), minute = int(mins), second = int(secs))
    debug_log(f'Scheduler info: ID: regular hour: {int(hrs)} min: {int(mins)} sec: {int(secs)}')
    if running:
        sched.resume()

def init_scheduler(server: ServerInterface):
    global sched
    if sched:
        sched.remove_all_jobs()
        sched.shutdown()
        del sched
    sched = BackgroundScheduler()
    set_scheduler(server, True)
    sched.start()
    if not config['enableAutoUpdate']:
        sched.pause()
        debug_log('Scheduler paused')

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

def get_general_path(server: ServerInterface):
    global data_folder, config_path, log_path, backup_folder
    data_folder = server.get_data_folder()
    config_path = os.path.join(data_folder, config_file)
    log_path = os.path.join(data_folder, log_file)
    backup_folder = os.path.join(data_folder, backup_dir)

def get_server_path():
    global server_path
    with open('config.yml', 'r', encoding = 'UTF-8') as f:
        content = yaml.round_trip_load(f)
    server_folder = content['working_directory']
    if not config['serverPath'].endswith('.jar'):
        server_file = content['start_command'].split(' ')[content['start_command'].split(' ').index('-jar') + 1]
    else:
        server_file = config['serverPath']
    server_path = os.path.join(server_folder, server_file)
    debug_log(f'Server JAR path: {server_path}')

def on_load(server: ServerInterface, prev_module):
    get_general_path(server)
    get_config()
    get_server_path()
    global update
    update = pendingUpdate()
    init_scheduler(server)
    register_stuffs(server)

def on_unload(server: ServerInterface):
    global sched
    if sched:
        sched.remove_all_jobs()
        sched.shutdown()
        del sched
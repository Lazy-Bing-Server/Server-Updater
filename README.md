# Server Updater
自动检查并获取**原版服务端**更新

**原版端，原版端，原版端！重要的事情嗦三遍。**（四遍了?!）

## 简介
本插件用于**纯原版服务端**（五遍了）的快速定时更新, fabric端没试过, 应该是用不了的

本插件会在每日特定时间检查服务端更新，若服务端里无人则直接更新服务端，有人则一段时间后重试, 重试时仍有人则将下一日同一时间再次检查更新

也可以直接强制更新服务端（这也是本插件虫最少的地方...）

## 依赖
[`MCDReforged`](http://github.com/Fallen-Breath/MCDReforged)`>= 1.5.0` (需要与服务端建立有效的`rcon`链接, 如果不知道怎么做请自行查阅MCDR文档)

[`APScheduler`](https://pypi.org/project/APScheduler/)(可使用`pip install APScheduler`安装, 建议先`pip install setuptools -U`更新本插件的依赖`setuptools`以保证`APScheduler`安装正确)

## 配置项
### 插件中
配置完请在游戏内`!!MCDR r plg`一下
#### `config_file`, `log_file`, `backup_dir`
分别是配置文件, 日志文件和本插件存放下载的和替换下的服务端文件的目录, 均为MCDR工作路径下`config/server_updater`下的相对路径

#### `prefix`
本插件的插件前缀, 默认`!!update`, 本说明无额外说明提及指令时前缀均为`!!update`

### 配置文件中
配置完请在游戏内`!!update reload`一下

#### `enableAutoUpdate`, `autoUpdateTime`, `checkSnapshot`, `forceAutoUpdate`, `playerInterruptRetryInterval`, `playerInterruptRetryTimes`, `hashFailRetryTimes`
这七项（下称"前七项"）可以在游戏内配置, 将在后面介绍

#### `serverPath`
如果MCDR配置文件中填写的`start_command`是`java -jar`直接启动服务端的指令, 那恭喜, 这项可以不用管了, 插件会自动读取的

如果MCDR配置文件中填写的启动指令是启动其他脚本或程序再指向服务端, 那烦请正确填写这一项

此项必须填写当前运行的**原版服务端**（六遍了...）在MCDR配置文件填写的`working_directory`目录下的**相对路径**

#### `verbose`
啰嗦模式, 为`true`时MCDR后台会输出一些调试插件用的日志

#### `permission`
执行各参数所需的最小MCDR权限等级, 其中`rule`项指游戏内配置前七项的权限要求, 其余项与指令参数相同

### 游戏中

#### 1. `bool` 类型

游戏内配置时可填写任意大小写的`true`或`false`, 修改配置文件时必须按照`YAML`语法填写正确的布尔值

##### `enableAutoUpdate`

为`True`时启用自动更新

##### `checkSnapshot`

为`True`时自动更新会检查是否是最新快照版本, 否则检查最新发布版本

##### `forceAutoUpdate`

为`True`时插件自动检查更新后会无视服务器内是否有玩家, 直接更新, 反之则不会, 更新操作因服务器内有玩家被取消后插件的行为由`playerInterruptRetryTimes`和`playerInterruptRetryTimes`决定

#### 2. 时间类型

须填写有效的24小时制时间(`hh:mm:ss`), 形如`11:45:14`, `19:1:9`和`8:1:0`都是可行的, 填写配置文件时与游戏内配置一致

##### `autoUpdateTime`

服务器每天会在本项规定的时间检查更新并执行自动更新操作

3.`int`类型

填写整数, 游戏内配置和文件中填写是一致的, 每项都有对应的大小限制, 若某项填写了错误的整数值时会在该项值调用时被重置为本项要求的最小值

##### `playerInterruptRetryInterval`和`playerInterruptRetryTimes`

当`forceAutoUpdate`为`false`时, 插件不会在服务器有玩家时重新启动服务端进行更新操作, 此时服务器会计划一个副计划任务, 在一段时间后(与`autoUpdateTime`配置的主计划任务无关)自动再次尝试更新, 并暂停主计划任务的执行

该间隔时间由`playerInterruptRetryInterval`决定, 须填写大于`0`的整数, 不建议填的太大(即接近或超过一天`1440`)

若再次尝试执行时服务器内仍有玩家, 服务器不会自动更新, 将在`playerInterruptRetryInterval`配置的时间段后再次执行, 最多不超过`playerInterruptRetryTimes`配置的次数, 该次数须大于等于`0`(等于`0`即取消再次执行, 直接恢复主计划任务)

为避免冲突, 副计划任务在任意前七项被修改时会被中止并恢复主计划任务的执行

##### `hashFailRetryTimes`

本插件下载服务端文件时会按照`Mojang`提供的`API`中的`SHA1`值对服务端文件进行散列值校验, `hashFailRetryTimes`项决定散列值校验失败时最多的重试次数, 该项不应小于`0`

## 插件指令

未注明的情况下此处的`!!update`均指本插件的指令前缀

### 1. `!!update`

显示本插件帮助信息

### 2. `!!update reload`

重载配置文件并重置计划任务

### 3.`!!update status`

显示服务端版本与最新版本信息, 以及插件配置项

### 4. `!!update now`

立即检查更新并更新服务端

### 5. `!!update <rule> <value>`

修改本插件的配置项`<rule>`的值为`<value>`具体配置项可见`!!update status`或本文档`配置项 - 游戏内`部分

当`value`为空时则仅显示该项当前配置和默认配置
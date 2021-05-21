# Server Updater
自动检查并获取**原版服务端**更新

**原版端，原版端，原版端！重要的事情嗦三遍。**（四遍了?!）

指令帮助就不写了, 自己搁游戏里看去罢(加载后输入`!!update`)

## *早期预览版本*
本插件处于早期预览阶段, 若确需使用, 请妥善备份包括但不限于服务器存档在内的一切有价值数据!!!数据无价!!!

**重要的事说三遍: 插件还没写完!!! 没写完!!! 没写完!!!**

**虫非常非常非常非常非常非常非常非常非常非常非常非常多!**

## 简介
本插件用于**纯原版服务端**（五遍了）的快速定时更新, fabric端没试过, 应该是用不了的

本插件会在每日特定时间检查服务端更新，若服务端里无人则直接更新服务端，有人则一段时间后重试, 重试时仍有人则将下一日同一时间再次检查更新

也可以直接强制更新服务端（这也是本插件虫最少的地方...）

## 依赖
[MCDReforged](http://github.com/Fallen-Breath/MCDReforged) >= 1.5.0 (需要与服务端建立有效的`rcon`链接, 如果不知道怎么做请自行查阅MCDR文档)

APScheduler 
(使用`pip install apscheduler`安装, 建议先`pip install setuptools -U`更新本插件的依赖`setuptools`以保证`APScheduler`安装正确)

## 配置项
### 插件中
配置完请在游戏内`!!MCDR r plg`一下
#### `config_file`, `log_file`, `backup_dir`
分别是配置文件, 日志文件和本插件存放下载的和替换下的服务端文件的目录, 均为MCDR工作路径下`config/server_updater`下的相对路径

#### `prefix`
本插件的插件前缀, 默认`!!update`, 本说明无额外说明提及指令时前缀均为`!!update`

### 配置文件中
配置完请在游戏内`!!update reload`一下

#### `enableAutoUpdate`, `autoUpdateTime`, `checkSnapshot`, `retryInterval`
这四项（下称"前四项"）可以在游戏内配置, 建议去游戏内看看, 不知道咋配置查`!!update status`

#### `serverPath`
如果MCDR配置文件中填写的`start_command`是`java -jar`直接启动服务端的指令, 那恭喜, 这项可以不用管了, 插件会自动读取的

如果MCDR配置文件中填写的启动指令是启动其他脚本或程序再指向服务端, 那烦请正确填写这一项

此项必须填写当前运行的**原版服务端**（六遍了...）在MCDR配置文件填写的`working_directory`目录下的**相对路径**

#### `verbose`
啰嗦模式, 为`true`时MCDR后台会输出一些调试插件用的日志

#### `permission`
执行各参数所需的最小MCDR权限等级, 其中`rule`项指游戏内配置前四项的权限要求, 其余项与指令参数相同

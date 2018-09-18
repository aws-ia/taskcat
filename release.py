import configparser as ConfigParser
import datetime

def get_version():
    _version = datetime.datetime.now().strftime("%Y.%-m%-d.%-H%-M")
    print("Creating new version {}".format(_version))
    return _version


Config = ConfigParser.RawConfigParser()
setupcfg_file='setup.cfg'
cfg = open(setupcfg_file, 'r')
Config.read_file(cfg)
cfg.close()

cfg = open(setupcfg_file, 'w')
Config.set('metadata','version', get_version())
Config.write(cfg)
cfg.close()

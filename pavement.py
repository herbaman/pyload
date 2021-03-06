# -*- coding: utf-8 -*-


from paver.easy import *
from paver.setuputils import setup

try:
    from paver.doctools import cog
except:
    cog = None

import fnmatch

# patch to let it support list of patterns
def new_fnmatch(self, pattern):
    if type(pattern) == list:
        for p in pattern:
            if fnmatch.fnmatch(self.name, p):
                return True
        return False
    else:
        return fnmatch.fnmatch(self.name, pattern)

path.fnmatch = new_fnmatch

import sys
import re
from urllib import urlretrieve
from subprocess import call, Popen
from zipfile import ZipFile

PROJECT_DIR = path(__file__).dirname()
sys.path.append(PROJECT_DIR)

options = environment.options
path('pyload').mkdir()

extradeps = []
if sys.version_info <= (2, 5):
    extradeps += 'simplejson'

setup(
    name="pyload",
    version="0.5.0",
    description='Fast, lightweight and full featured download manager.',
    long_description=open(PROJECT_DIR / "README.md").read(),
    keywords=('pyload', 'download-manager', 'one-click-hoster', 'download'),
    url="http://pyload.org",
    download_url='http://pyload.org/download',
    license='AGPL v3',
    author="pyLoad Team",
    author_email="support@pyload.org",
    platforms=('Any',),
    #package_dir={'pyload': 'src'},
    packages=['pyload'],
    #package_data=find_package_data(),
    #data_files=[],
    include_package_data=True,
    exclude_package_data={'pyload': ['docs*', 'scripts*', 'tests*']}, #exluced from build but not from sdist
    # 'bottle >= 0.10.0' not in list, because its small and contain little modifications
    install_requires=['pycurl', 'jinja2 >= 2.6', 'Beaker >= 1.6'] + extradeps,
    tests_require=['websocket-client >= 0.8.0'],
    extras_require={
        'SSL': ["pyOpenSSL"],
        'DLC': ['pycrypto'],
        'Lightweight webserver': ['bjoern'],
        'RSS plugins': ['feedparser'],
        'Few Hoster plugins': ['BeautifulSoup>=3.2, <3.3']
    },
    #setup_requires=["setuptools_hg"],
    entry_points={
        'console_scripts': [
            'pyload = pyload:main',
            'pyload-cli = pyload_cli:main' #TODO fix
        ]},
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Internet :: WWW/HTTP",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2"
    ]
)

options(
    sphinx=Bunch(
        builddir="_build",
        sourcedir=""
    ),
    get_source=Bunch(
        src="https://bitbucket.org/spoob/pyload/get/tip.zip",
        rev=None,
        clean=False
    ),
    apitypes=Bunch(
        path="thrift",
    ),
    optimize_js=Bunch(
        r="r.js"
    ),
    virtualenv=Bunch(
        dir="env",
        python="python2",
        virtual="virtualenv2",
    ),
    cog=Bunch(
        pattern=["*.py", "*.rst"],
    )
)

# xgettext args
xargs = ["--from-code=utf-8", "--copyright-holder=pyLoad Team", "--package-name=pyLoad",
         "--package-version=%s" % options.version, "--msgid-bugs-address='bugs@pyload.org'"]

@task
@needs('cog')
def html():
    """Build html documentation"""
    module = path("docs") / "module"
    module.rmtree()
    call_task('paver.doctools.html')


@task
@cmdopts([
    ('src=', 's', 'Url to source'),
    ('rev=', 'r', "HG revision"),
    ("clean", 'c', 'Delete old source folder')
])
def get_source(options):
    """ Downloads pyload source from bitbucket tip or given rev"""
    if options.rev: options.url = "https://bitbucket.org/spoob/pyload/get/%s.zip" % options.rev

    pyload = path("pyload")

    if len(pyload.listdir()) and not options.clean:
        return
    elif pyload.exists():
        pyload.rmtree()

    urlretrieve(options.src, "pyload_src.zip")
    zip = ZipFile("pyload_src.zip")
    zip.extractall()
    path("pyload_src.zip").remove()

    folder = [x for x in path(".").dirs() if x.name.startswith("spoob-pyload-")][0]
    folder.move(pyload)

    change_mode(pyload, 0644)
    change_mode(pyload, 0755, folder=True)

    for file in pyload.files():
        if file.name.endswith(".py"):
            file.chmod(0755)

    (pyload / ".hgtags").remove()
    (pyload / ".hgignore").remove()
    #(pyload / "docs").rmtree()

    f = open(pyload / "__init__.py", "wb")
    f.close()

    #options.setup.packages = find_packages()
    #options.setup.package_data = find_package_data()


@task
@needs('clean', 'generate_setup', 'get_source', 'setuptools.command.sdist')
def sdist():
    """ Build source code package with distutils """


@task
@cmdopts([
    ('path=', 'p', 'Thrift path'),
])
def apitypes(options):
    """ Generate data types stubs """

    outdir = PROJECT_DIR / "module" / "remote"

    if (outdir / "gen-py").exists():
        (outdir / "gen-py").rmtree()

    cmd = [options.apitypes.path, "-strict", "-o", outdir, "--gen", "py:slots,dynamic", outdir / "pyload.thrift"]

    print "running", cmd

    p = Popen(cmd)
    p.communicate()

    (outdir / "thriftgen").rmtree()
    (outdir / "gen-py").move(outdir / "thriftgen")

    #create light ttypes
    from module.remote.create_apitypes import main
    main()
    from module.remote.create_jstypes import main
    main()


@task
@cmdopts([
    ('r=', 'r', 'R.js path')
])
def optimize_js(options):
    """ Generate optimized version of the js code """

    webdir = PROJECT_DIR / "module" / "web" / "static"
    target = webdir / "js" / "app.build.js"

    (webdir / "js-optimized").rmtree()

    cmd = ["node", options.optimize_js.r, "-o", target]

    print "running", cmd
    p = Popen(cmd)
    p.communicate()


@task
def load_icons():
    """ Load fontawesome icons """
    import json, requests

    f = PROJECT_DIR / "module" / "web" / "static" / "fonts" / "fontawesome.txt"
    icons = [line.split() for line in open(f, "rb").read().splitlines() if not line.startswith("#")]
    icons = [{"name": n, "uni": u, "file": "", "selected": True} for n, u in icons]

    r = requests.post("http://www.icnfnt.com/api/createpack", data={"json_data": json.dumps(icons)})
    r = requests.get("http://www.icnfnt.com" + r.text)

    zip = path("/tmp") / "fontawesome.zip"
    f = open(zip, "wb")
    f.write(r.content)
    f.close()

    call(["unzip", zip, "-d", "/tmp"])

    css = open("/tmp/fontawesome.css", "rb").read()
    css = css.replace("icon-", "iconf-").replace("fontawesome-webfont", "../fonts/fontawesome-webfont")

    f = open(PROJECT_DIR / "module" / "web" / "static" / "css" / "fontawesome.css", "wb")
    f.write(css)
    f.close()

    from glob import glob
    from shutil import copy
    for f in glob("/tmp/fontawesome-webfont.*"):
        copy(f, PROJECT_DIR / "module" / "web" / "static" / "fonts")

@task
def generate_locale():
    """ Generates localisation files """

    EXCLUDE = ["BeautifulSoup.py", "module/gui", "module/cli", "web/locale", "web/ajax", "web/cnl", "web/pyload",
               "setup.py"]
    makepot("core", path("module"), EXCLUDE, "./pyLoadCore.py\n")

    makepot("cli", path("module") / "cli", [], includes="./pyLoadCli.py\n")
    makepot("setup", "", [], includes="./module/setup.py\n")

    EXCLUDE = ["ServerThread.py", "web/media/default"]

    # strings from js files
    strings = set()

    for fi in path("module/web").walkfiles():
        if not fi.name.endswith(".js") and not fi.endswith(".coffee"): continue
        with open(fi, "rb") as c:
            content = c.read()

            strings.update(re.findall(r"_\s*\(\s*\"([^\"]+)", content))
            strings.update(re.findall(r"_\s*\(\s*\'([^\']+)", content))

    trans = path("module") / "web" / "translations.js"

    with open(trans, "wb") as js:
        for s in strings:
            js.write('_("%s")\n' % s)

    makepot("web", path("module/web"), EXCLUDE, "./%s\n" % trans.relpath(), [".py", ".html"], ["--language=Python"])

    trans.remove()

    path("includes.txt").remove()

    print "Locale generated"


@task
def tests():
    """ Run nosetests """
    call(["tests/nosetests.sh"])


@task
def virtualenv(options):
    """Setup virtual environment"""
    if path(options.dir).exists():
        return

    call([options.virtual, "--no-site-packages", "--python", options.python, options.dir])
    print "$ source %s/bin/activate" % options.dir


@task
def clean_env():
    """Deletes the virtual environment"""
    env = path(options.virtualenv.dir)
    if env.exists():
        env.rmtree()


@task
@needs('generate_setup', 'get_source', 'virtualenv')
def env_install():
    """Install pyLoad into the virtualenv"""
    venv = options.virtualenv
    call([path(venv.dir) / "bin" / "easy_install", "."])


@task
def clean():
    """Cleans build directories"""
    path("build").rmtree()
    path("dist").rmtree()


#helper functions

def walk_trans(path, EXCLUDE, endings=[".py"]):
    result = ""

    for f in path.walkfiles():
        if [True for x in EXCLUDE if x in f.dirname().relpath()]: continue
        if f.name in EXCLUDE: continue

        for e in endings:
            if f.name.endswith(e):
                result += "./%s\n" % f.relpath()
                break

    return result


def makepot(domain, p, excludes=[], includes="", endings=[".py"], xxargs=[]):
    print "Generate %s.pot" % domain

    f = open("includes.txt", "wb")
    if includes:
        f.write(includes)

    if p:
        f.write(walk_trans(path(p), excludes, endings))

    f.close()

    call(["xgettext", "--files-from=includes.txt", "--default-domain=%s" % domain] + xargs + xxargs)

    # replace charset und move file
    with open("%s.po" % domain, "rb") as f:
        content = f.read()

    path("%s.po" % domain).remove()
    content = content.replace("charset=CHARSET", "charset=UTF-8")

    with open("locale/%s.pot" % domain, "wb") as f:
        f.write(content)


def change_owner(dir, uid, gid):
    for p in dir.walk():
        p.chown(uid, gid)


def change_mode(dir, mode, folder=False):
    for p in dir.walk():
        if folder and p.isdir():
            p.chmod(mode)
        elif p.isfile() and not folder:
            p.chmod(mode)

#!/usr/bin/env python

import argparse
import errno
import os
import subprocess
import sys
import textwrap

from snakeoil.dist.generate_man_rsts import ManConverter


def generate_man(project, project_dir):
    print('Generating files for man pages')

    try:
        os.mkdir('generated')
    except OSError as e:
        if e.errno == errno.EEXIST:
            return
        raise

    scripts = os.listdir(os.path.abspath(os.path.join(project_dir, 'bin')))

    # Replace '-' with '_' due to python namespace contraints.
    generated_man_pages = [
        ('%s.scripts.' % (project) + s.replace('-', '_'), s) for s in scripts
    ]

    for module, script in generated_man_pages:
        rst = script + '.rst'
        # generate missing, generic man pages
        if not os.path.isfile(os.path.join('man', rst)):
            with open(os.path.join('generated', rst), 'w') as f:
                f.write(textwrap.dedent("""\
                    {header}
                    {script}
                    {header}

                    .. include:: {script}/main_synopsis.rst
                    .. include:: {script}/main_description.rst
                    .. include:: {script}/main_options.rst
                """.format(header=('=' * len(script)), script=script)))
            os.symlink(os.path.join(os.pardir, 'generated', rst), os.path.join('man', rst))
        os.symlink(os.path.join(os.pardir, 'generated', script), os.path.join('man', script))
        ManConverter.regen_if_needed('generated', module, out_name=script)


def generate_html(module_dir):
    print('Generating API docs')
    subprocess.call([
        'sphinx-apidoc', '-Tef', '-o', 'api', module_dir, os.path.join(module_dir, 'test')])


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='generate docs')
    argparser.add_argument('--man', action='store_true', help='generate man files')
    argparser.add_argument('--html', action='store_true', help='generate API files')
    argparser.add_argument(
        'project', nargs=2, metavar='PROJECT_DIR PROJECT',
        help='project root directory and main module name')

    opts = argparser.parse_args()
    opts.project_dir = os.path.abspath(opts.project[0])
    opts.project = opts.project[1]
    opts.module_dir = os.path.join(opts.project_dir, opts.project)

    libdir = os.path.abspath(os.path.join(opts.project_dir, 'build', 'lib'))
    if os.path.exists(libdir):
        sys.path.insert(0, libdir)
    sys.path.insert(1, opts.project_dir)

    # if run with no args, build all docs
    if not opts.man and not opts.html:
        opts.man = opts.html = True

    if opts.man:
        generate_man(opts.project, opts.project_dir)

    if opts.html:
        generate_html(opts.module_dir)

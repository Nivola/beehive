'''
Created on Nov 3, 2017

@author: darkbk
'''
import click

@click.group(chain=True)
def cli3():
    """First paragraph.

    This is a very long second paragraph and as you
    can see wrapped very early in the source text
    but will be rewrapped to the terminal width in
    the final output.

    \b
    This is
    a paragraph
    without rewrapping.

    And this is a paragraph
    that will be rewrapped again.
    """    
    pass

@cli3.command('sdist')
def sdist():
    click.echo('sdist called')

@cli3.command('bdist_wheel')
def bdist_wheel():
    click.echo('bdist_wheel called')

@click.group()
def cli1():
    pass

@cli1.command()
def cmd1():
    """Command on cli1"""

@click.group()
def cli2():
    pass

@cli2.command()
def cmd2():
    """Command on cli2"""
    
@click.group()
def cli4():
    pass

@cli4.command()
def cmd3():
    """Command on cli2"""
    cli3()

cli = click.CommandCollection(sources=[cli1, cli2, cli4])

if __name__ == '__main__':
    cli()
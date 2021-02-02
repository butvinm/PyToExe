import os
import subprocess
import sys

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.behaviors import HoverBehavior
from kivymd.uix.button import MDIconButton
from kivymd.uix.gridlayout import MDGridLayout


class MainWidget(MDGridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'escape':
            self.app_cls.change_size()
        return True

    def on_touch_down(self, touch):
        if len(self.get_root_window().children) == 1:
            return super().on_touch_down(touch)
        return


class TitleBar(MDGridLayout):
    touch_x = 0
    touch_y = 0
    moveable = False

    def on_touch_down(self, touch):
        if (
            self.collide_point(*touch.pos)
            and not self.children[0].children[0].collide_point(*touch.pos)
            and not self.children[1].children[0].collide_point(*touch.pos)
        ):
            self.moveable = True
            self.touch_x, self.touch_y = touch.pos
        else:
            self.moveable = False

        return super().on_touch_down(touch)

    def on_touch_move(self, touch):

        if self.collide_point(*touch.pos) and self.moveable:
            if Window.size == self.parent.app_cls.display_size:
                Window.size = (Window.width // 1.1, Window.height)
            Window.left += touch.x - self.touch_x
            Window.top -= touch.y - self.touch_y
        return super().on_touch_move(touch)


class TitleBarButton(MDIconButton, HoverBehavior):
    def on_enter(self, *args):
        self.md_bg_color = self.theme_cls.bg_dark

    def on_leave(self, *args):
        self.md_bg_color = self.theme_cls.bg_darkest


class InfoBanner(MDGridLayout):
    pass


class App(MDApp):
    def build(self):
        # Доступ к file.txt только так
        with open(resource_path('PyToExe.kv'), 'r') as file:
            Builder.load_string(file.read())
            pass
        self.font = resource_path('Roboto-Light.ttf')

        self.theme_cls.primary_palette = 'Gray'
        self.theme_cls.theme_style = 'Dark'

        Window.borderless = 1
        Window.fullscreen = "auto"  # disable later
        self.display_size = (0, 0)
        Clock.schedule_once(self.apply_display_size)

        self.command = ['--noconsole', '--onedir']
        self.path = ('', '')
        self.process = None
        Clock.schedule_interval(self.update_cmd, 2)
        Clock.max_iteration = 1000000

        self.main_widget = MainWidget()
        self.main_widget.ids['command'].children[0].text = \
            '    '.join(self.command)
        return self.main_widget

    def apply_display_size(self, *args):
        print('apply display size')
        self.display_size = Window.width-1, Window.height
        Window.fullscreen = False
        Window.size = self.display_size
        Window.top, Window.left = 0, 0

    def change_size(self):
        if Window.size == self.display_size:
            Window.size = (Window.width // 2, Window.height)
        else:
            Window.size = self.display_size
        Window.top, Window.left = 0, 0
    
    def separate_path(self, path):
        splitter = ''

        if '//' in path:
            splitter = '//'
        elif '\\\\' in path:
            splitter = '\\\\'
        elif '/' in path:
            splitter = '/'
        elif '\\' in path:
            splitter = '\\'

        folder = path[:(path.rfind(splitter)+len(splitter))]
        file = path[(path.rfind(splitter)+len(splitter)):]
        return folder, file

    def update_command(self):
        widgets = dict([
            (widget[0], widget[1].children[0].text)
            for widget in self.main_widget.ids.items()
            if not 'cb' in widget[0]
        ])
        widgets.pop('command')

        self.command = []

        if self.main_widget.ids['cb_console'].children[1].active:
            self.command.append('--console')
        else:
            self.command.append('--noconsole')

        if self.main_widget.ids['cb_one_file'].children[1].active:
            self.command.append('--onefile')
        else:
            self.command.append('--onedir')

        for widget in widgets.copy().items():
            if widget[1].strip():
                if widget[0] == 'file_name':
                    self.command.append(f'--name {widget[1]}')

                elif widget[0] == 'icon_path':
                    self.command.append(f'--icon="{widget[1]}"')

                elif widget[0] in ('data', 'binary'):
                    s = widget[1].replace(' ', '')
                    s = s.replace('(', '')
                    s = s.replace(')', '')
                    path_pairs = s.split(',')
                    for pair in path_pairs:
                        self.command.append(f'--add-{widget[0]}="{pair}"')

                elif widget[0] in ('hidden-import', 'exclude-module'):
                    s = widget[1].replace(' ', '')
                    module_names = widget[1].split(';')
                    for module in module_names:
                        self.command.append(f'--{widget[0]} {module}')

        self.path = self.separate_path(widgets['file_path'])
        self.command.append(self.path[1])

        self.main_widget.ids['command'].children[0].text = '    '.join(
            self.command)

    def update_cmd(self, time):
        if self.process:
            output = self.process.stdout.readlines()
            text = '\n'.join(list(map(lambda s: s.decode('utf-8'), output)))
            self.main_widget.ids['cmd'].children[0].text = text
            self.process = None

    def run_command(self, button):
        if self.process:
            return 0
        
        self.main_widget.ids['cmd'].children[0].text = 'Command is executed...'
        
        if button == 'Create Exe':
            action = 'pyinstaller'
        else:
            action = 'pyi-makespec'

        command = ' '.join(['cd', self.path[0], '&&', action] + self.command)

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )

    def show_info(self):
        self.root_window.add_widget(InfoBanner())


def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    else:
        return os.path.join(os.path.abspath("."), relative)


def main():
    print('main method')
    App().run()


if __name__ == '__main__':
    main()

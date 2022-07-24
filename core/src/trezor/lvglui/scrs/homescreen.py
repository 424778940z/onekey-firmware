import math

from storage import device
from trezor import utils, workflow
from trezor.langs import langs, langs_keys
from trezor.lvglui.i18n import gettext as _, i18n_refresh, keys as i18n_keys
from trezor.lvglui.lv_colors import lv_colors
from trezor.ui import display

from . import font_LANG_MIX, font_PJSBOLD24, font_PJSBOLD36, font_PJSREG24
from .common import (  # noqa: F401, F403, F405
    FullSizeWindow,
    Screen,
    load_scr_with_animation,
    lv,
)
from .components.anim import Anim
from .components.button import ListItemBtn, ListItemBtnWithSwitch
from .components.container import ContainerFlexCol, ContanierGrid
from .components.imgbtn import ImgBottonGridItem
from .components.listitem import DisplayItem


def brightness2_percent_str(brightness: int) -> str:
    return f"{int(brightness / 255 * 100)}%"


GRID_CELL_SIZE = 128


def change_state(is_busy: bool = False):
    if hasattr(MainScreen, "_instance"):
        if MainScreen._instance.is_visible():
            MainScreen._instance.change_state(is_busy)


class MainScreen(Screen):
    def __init__(self, device_name=None, ble_name=None, dev_state=None):
        cur_index = device.get_wp_index()
        homescreen = f"A:/res/wallpaper-{cur_index+1}.png"
        if not hasattr(self, "_init"):
            self._init = True
        else:
            if dev_state:
                self.dev_state.clear_flag(lv.obj.FLAG.HIDDEN)
                self.dev_state_text.set_text(dev_state)
            else:
                from apps.base import get_state

                state = get_state()
                if state:
                    self.dev_state.clear_flag(lv.obj.FLAG.HIDDEN)
                    self.dev_state_text.set_text(state)
                else:
                    self.dev_state.add_flag(lv.obj.FLAG.HIDDEN)
            self.set_style_bg_img_src(homescreen, lv.PART.MAIN | lv.STATE.DEFAULT)
            if self.bottom_tips:
                self.bottom_tips.set_text(_(i18n_keys.BUTTON__SWIPE_TO_SHOW_APPS))
            if self.apps:
                self.apps.tips_top.set_text(_(i18n_keys.BUTTON__CLOSE))
            if not self.is_visible():
                load_scr_with_animation(self)
            return
        super().__init__(title=device_name, subtitle=ble_name)
        self.title.align(lv.ALIGN.TOP_MID, 0, 92)
        self.subtitle.set_style_text_color(
            lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.dev_state = lv.btn(self)
        self.dev_state.set_size(lv.pct(96), lv.SIZE.CONTENT)
        self.dev_state.set_style_bg_color(
            lv.color_hex(0xDCA312), lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.dev_state.set_style_radius(8, lv.PART.MAIN | lv.STATE.DEFAULT)
        self.dev_state.align(lv.ALIGN.TOP_MID, 0, 52)
        self.dev_state_text = lv.label(self.dev_state)
        self.dev_state_text.set_style_text_color(
            lv_colors.BLACK, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.dev_state_text.set_style_text_font(
            font_PJSBOLD24, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.dev_state_text.center()
        if dev_state:
            self.dev_state_text.set_text(dev_state)
        else:
            self.dev_state.add_flag(lv.obj.FLAG.HIDDEN)
        self.set_style_bg_img_src(homescreen, lv.PART.MAIN | lv.STATE.DEFAULT)
        self.set_style_bg_img_opa(255, lv.PART.MAIN | lv.STATE.DEFAULT)
        self.clear_flag(lv.obj.FLAG.SCROLLABLE)
        self.bottom_bar = lv.btn(self)
        self.bottom_bar.remove_style_all()
        self.bottom_bar.set_size(lv.pct(100), 100)
        self.bottom_bar.set_align(lv.ALIGN.BOTTOM_MID)
        self.up_arrow = lv.img(self.bottom_bar)
        self.up_arrow.set_src("A:/res/up-home.png")
        self.up_arrow.set_align(lv.ALIGN.TOP_MID)
        self.bottom_tips = lv.label(self.bottom_bar)
        self.bottom_tips.align(lv.ALIGN.BOTTOM_MID, 0, -16)
        self.bottom_tips.set_text(_(i18n_keys.BUTTON__SWIPE_TO_SHOW_APPS))
        self.bottom_tips.set_style_text_font(
            font_PJSBOLD24, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.bottom_tips.set_style_text_color(
            lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.apps = None
        self.add_event_cb(self.on_slide_up, lv.EVENT.GESTURE, None)

    def hidden_titles(self, hidden: bool = True):
        if hidden:
            self.subtitle.add_flag(lv.obj.FLAG.HIDDEN)
            self.title.add_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.subtitle.clear_flag(lv.obj.FLAG.HIDDEN)
            self.title.clear_flag(lv.obj.FLAG.HIDDEN)

    def change_state(self, busy: bool):
        if busy:
            self.clear_flag(lv.obj.FLAG.CLICKABLE)
            self.up_arrow.add_flag(lv.obj.FLAG.HIDDEN)
            self.bottom_tips.set_text(_(i18n_keys.BUTTON__PROCESSING))
        else:
            self.add_flag(lv.obj.FLAG.CLICKABLE)
            self.up_arrow.clear_flag(lv.obj.FLAG.HIDDEN)
            self.bottom_tips.set_text(_(i18n_keys.BUTTON__SWIPE_TO_SHOW_APPS))

    def on_slide_up(self, event_obj):
        code = event_obj.code
        if code == lv.EVENT.GESTURE:
            _dir = lv.indev_get_act().get_gesture_dir()
            if _dir == lv.DIR.TOP:
                # child_cnt == 4 in common if in homepage
                if self.get_child_cnt() > 4:
                    return
                if self.is_visible() and self.apps is None:
                    self.hidden_titles()
                    self.apps = self.AppDrawer(self)
            elif _dir == lv.DIR.BOTTOM:
                lv.event_send(self.apps, lv.EVENT.GESTURE, None)

    class AppDrawer(lv.obj):
        def __init__(self, parent) -> None:
            super().__init__(parent)
            self.parent = parent
            self.remove_style_all()
            self.set_pos(0, 148)
            self.set_size(lv.pct(100), 652)
            # header
            self.header = lv.obj(self)
            self.header.remove_style_all()
            self.header.set_size(lv.pct(100), 100)
            self.header.set_align(lv.ALIGN.TOP_MID)
            self.header.add_flag(lv.obj.FLAG.EVENT_BUBBLE)
            self.tips_top = lv.label(self.header)
            self.tips_top.set_style_text_font(
                font_PJSBOLD24, lv.PART.MAIN | lv.STATE.DEFAULT
            )
            self.tips_top.set_style_text_color(
                lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
            )
            self.tips_top.set_text(_(i18n_keys.BUTTON__CLOSE))
            self.tips_top.align(lv.ALIGN.TOP_MID, 0, 16)
            self.down_img = lv.img(self.header)
            self.down_img.set_src("A:/res/down-home.png")
            self.down_img.align_to(self.tips_top, lv.ALIGN.OUT_BOTTOM_MID, 0, 8)
            # content panel
            self.panel = lv.obj(self)
            self.panel.remove_style_all()
            self.panel.set_size(lv.pct(100), 552)
            self.panel.align_to(self.down_img, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)
            self.panel.set_style_bg_color(
                lv_colors.WHITE_3, lv.PART.MAIN | lv.STATE.DEFAULT
            )
            self.panel.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN | lv.STATE.DEFAULT)
            self.panel.set_style_radius(30, lv.PART.MAIN | lv.STATE.DEFAULT)
            self.panel.add_flag(lv.obj.FLAG.EVENT_BUBBLE)
            # mask
            self.mask = lv.obj(self)
            self.mask.remove_style_all()
            self.mask.set_size(lv.pct(100), 40)
            self.mask.set_style_bg_color(
                lv_colors.WHITE_3, lv.PART.MAIN | lv.STATE.DEFAULT
            )
            self.mask.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN | lv.STATE.DEFAULT)
            self.mask.set_align(lv.ALIGN.BOTTOM_MID)

            # buttons
            self.settings = lv.imgbtn(self.panel)
            self.settings.set_pos(80, 48)
            self.settings.set_style_bg_img_src(
                "A:/res/settings.png", lv.PART.MAIN | lv.STATE.DEFAULT
            )
            self.settings.add_flag(lv.obj.FLAG.EVENT_BUBBLE)
            self.guide = lv.imgbtn(self.panel)
            self.guide.align_to(self.settings, lv.ALIGN.OUT_RIGHT_MID, 64, 0)
            self.guide.set_style_bg_img_src(
                "A:/res/guide.png", lv.PART.MAIN | lv.STATE.DEFAULT
            )
            self.guide.add_flag(lv.obj.FLAG.EVENT_BUBBLE)
            self.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)
            self.add_event_cb(self.on_slide_down, lv.EVENT.GESTURE, None)
            self.show_anim = Anim(800, 148, self.set_pos, time=30)
            self.show_anim.start()
            self.dismiss_anim = Anim(
                148, 800, self.set_pos, time=70, path_cb=lv.anim_t.path_ease_out
            )
            self.slide = False

        def clear(self):
            if self.is_visible():
                self.del_delayed(200)
                self.parent.apps = None
                self.parent.hidden_titles(False)
                self.header.add_flag(lv.obj.FLAG.HIDDEN)
                self.dismiss_anim.start()

        def on_click(self, event_obj):
            code = event_obj.code
            target = event_obj.get_target()
            if code == lv.EVENT.CLICKED and not self.slide:
                if target == self.settings:
                    SettingsScreen(self.parent)
                elif target == self.guide:
                    UserGuide(self.parent)
                elif target == self.header:
                    self.clear()

        def on_slide_down(self, event_obj):
            code = event_obj.code
            if code == lv.EVENT.GESTURE:
                _dir = lv.indev_get_act().get_gesture_dir()
                if _dir == lv.DIR.BOTTOM:
                    self.slide = True
                    self.clear()


class SettingsScreen(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            self.refresh_text()
            if not self.is_visible():
                load_scr_with_animation(self)
            return
        kwargs = {
            "prev_scr": prev_scr,
            "title": _(i18n_keys.TITLE__SETTINGS),
            "nav_back": True,
        }
        super().__init__(**kwargs)
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.general = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__GENERAL),
            left_img_src="A:/res/general.png",
        )
        self.connect = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__CONNECT),
            left_img_src="A:/res/connect.png",
        )
        self.home_scr = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__HOME_SCREEN),
            left_img_src="A:/res/homescreen.png",
        )
        self.security = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__SECURITY),
            left_img_src="A:/res/security.png",
        )
        # self.crypto = ListItemBtn(
        #     self.container, _(i18n_keys.FORM__CRYPTO), left_img_src="A:/res/crypto.png"
        # )
        self.about = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__ABOUT_DEVICE),
            left_img_src="A:/res/about.png",
        )
        self.power = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__POWER_OFF),
            left_img_src="A:/res/poweroff.png",
            has_next=False,
        )
        self.power.label_left.set_style_text_color(
            lv_colors.ONEKEY_RED_1, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def refresh_text(self):
        self.title.set_text(_(i18n_keys.TITLE__SETTINGS))
        self.general.label_left.set_text(_(i18n_keys.ITEM__GENERAL))
        self.connect.label_left.set_text(_(i18n_keys.ITEM__CONNECT))
        self.home_scr.label_left.set_text(_(i18n_keys.ITEM__HOME_SCREEN))
        self.security.label_left.set_text(_(i18n_keys.ITEM__SECURITY))
        self.about.label_left.set_text(_(i18n_keys.ITEM__ABOUT_DEVICE))
        self.power.label_left.set_text(_(i18n_keys.ITEM__POWER_OFF))

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if utils.lcd_resume():
                return
            if target == self.general:
                GeneralScreen(self)
            elif target == self.connect:
                ConnectSetting(self)
            elif target == self.home_scr:
                HomeScreenSetting(self)
            elif target == self.security:
                SecurityScreen(self)
            # elif target == self.crypto:
            #     CryptoScreen(self)
            elif target == self.about:
                AboutSetting(self)
            elif target == self.power:
                PowerOff()
            else:
                if __debug__:
                    print("Unknown")


class GeneralScreen(Screen):
    cur_auto_lock = ""
    cur_auto_lock_ms = 0
    cur_language = ""

    def __init__(self, prev_scr=None):
        GeneralScreen.cur_auto_lock_ms = device.get_autolock_delay_ms()
        GeneralScreen.cur_auto_lock = self.get_str_from_lock_ms(
            GeneralScreen.cur_auto_lock_ms
        )
        if not hasattr(self, "_init"):
            self._init = True
        else:
            if self.cur_auto_lock_ms:
                self.auto_lock.label_right.set_text(GeneralScreen.cur_auto_lock)
            if self.cur_language:
                self.language.label_right.set_text(self.cur_language)
            self.backlight.label_right.set_text(
                brightness2_percent_str(device.get_brightness())
            )
            self.refresh_text()
            return
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__GENERAL), nav_back=True
        )
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.auto_lock = ListItemBtn(
            self.container, _(i18n_keys.ITEM__AUTO_LOCK), self.cur_auto_lock
        )
        GeneralScreen.cur_language = langs[langs_keys.index(device.get_language())][1]
        self.language = ListItemBtn(
            self.container, _(i18n_keys.ITEM__LANGUAGE), GeneralScreen.cur_language
        )
        self.backlight = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__BRIGHTNESS),
            brightness2_percent_str(device.get_brightness()),
        )
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def refresh_text(self):
        self.title.set_text(_(i18n_keys.TITLE__GENERAL))
        self.auto_lock.label_left.set_text(_(i18n_keys.ITEM__AUTO_LOCK))
        self.language.label_left.set_text(_(i18n_keys.ITEM__LANGUAGE))
        self.backlight.label_left.set_text(_(i18n_keys.ITEM__BRIGHTNESS))

    def get_str_from_lock_ms(self, time_ms) -> str:
        if time_ms == device.AUTOLOCK_DELAY_MAXIMUM:
            return _(i18n_keys.ITEM__STATUS__NEVER)
        auto_lock_time = time_ms / 1000 // 60
        if auto_lock_time > 60:
            text = _(i18n_keys.OPTION__STR_HOUR).format(
                str(auto_lock_time // 60).split(".")[0]
            )
        else:
            text = _(i18n_keys.ITEM__STATUS__STR_MINUTES).format(
                str(auto_lock_time).split(".")[0]
            )
        return text

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if utils.lcd_resume():
                return
            if target == self.auto_lock:
                AutoLockSetting(self)
            elif target == self.language:
                LanguageSetting(self)
            elif target == self.backlight:
                BacklightSetting(self)
            else:
                pass


# pyright: off
class AutoLockSetting(Screen):
    # TODO: i18n
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__AUTO_LOCK), nav_back=True
        )
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.setting_items = [1, 2, 5, 10, 30, "Never"]
        has_custom = True
        self.checked_index = 0
        self.btns = [None] * (len(self.setting_items) + 1)
        for index, item in enumerate(self.setting_items):
            if not item == "Never":  # last item
                item = _(i18n_keys.ITEM__STATUS__STR_MINUTES).format(item)
            else:
                item = _(i18n_keys.ITEM__STATUS__NEVER)
            self.btns[index] = ListItemBtn(self.container, item, has_next=False)
            self.btns[index].add_check_img()
            if item == GeneralScreen.cur_auto_lock:
                has_custom = False
                self.btns[index].set_checked()
                self.checked_index = index

        if has_custom:
            self.btns[-1] = ListItemBtn(
                self.container,
                f"{GeneralScreen.cur_auto_lock}({_(i18n_keys.OPTION__CUSTOM__INSERT)})",
                has_next=False,
            )
            self.btns[-1].add_check_img()  # type: ignore[Cannot access member "add_check_img" for type "None"]
            self.btns[-1].set_checked()  # type: ignore[Cannot access member "set_checked" for type "None"]
            self.checked_index = -1
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if utils.lcd_resume():
                return
            if target in self.btns:
                for index, item in enumerate(self.btns):
                    if item == target and self.checked_index != index:
                        item.set_checked()  # type: ignore[Cannot access member "set_checked" for type "None"]
                        self.btns[self.checked_index].set_uncheck()  # type: ignore[Cannot access member "set_uncheck" for type "None"]
                        self.checked_index = index
                        if index == 5:
                            auto_lock_time = device.AUTOLOCK_DELAY_MAXIMUM
                        elif index == 6:
                            auto_lock_time = int(GeneralScreen.cur_auto_lock_ms)
                        else:
                            auto_lock_time = self.setting_items[index] * 60 * 1000
                        device.set_autolock_delay_ms(auto_lock_time)
                        GeneralScreen.cur_auto_lock_ms = auto_lock_time
                        from apps.base import reload_settings_from_storage

                        reload_settings_from_storage()


# pyright: on
class LanguageSetting(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__LANGUAGE), nav_back=True
        )
        self.check_index = 0
        self.title.set_style_text_font(font_PJSBOLD36, lv.PART.MAIN | lv.STATE.DEFAULT)
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.lang_buttons = []
        for idx, lang in enumerate(langs):
            lang_button = ListItemBtn(self.container, lang[1], has_next=False)
            lang_button.label_left.set_style_text_font(
                font_LANG_MIX, lv.PART.MAIN | lv.STATE.DEFAULT
            )
            lang_button.add_check_img()
            self.lang_buttons.append(lang_button)
            if GeneralScreen.cur_language == lang[1]:
                lang_button.set_checked()
                self.check_index = idx
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if utils.lcd_resume():
                return
            last_checked = self.check_index
            for idx, button in enumerate(self.lang_buttons):
                if target != button and idx == last_checked:
                    button.set_uncheck()
                if target == button and idx != last_checked:
                    device.set_language(langs_keys[idx])
                    GeneralScreen.cur_language = langs[idx][1]
                    i18n_refresh()
                    self.title.set_text(_(i18n_keys.TITLE__LANGUAGE))
                    self.check_index = idx
                    button.set_checked()


class BacklightSetting(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__BRIGHTNESS), nav_back=True
        )
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        current_brightness = device.get_brightness()
        self.item1 = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__BRIGHTNESS),
            brightness2_percent_str(current_brightness),
            has_next=False,
        )
        self.slider = lv.slider(self)
        self.slider.set_style_border_width(0, lv.PART.MAIN | lv.STATE.DEFAULT)
        self.slider.set_size(424, 8)
        self.slider.set_ext_click_area(100)
        self.slider.set_range(20, 255)
        self.slider.set_value(current_brightness, lv.ANIM.OFF)
        self.slider.align_to(self.container, lv.ALIGN.BOTTOM_MID, 0, 33)
        self.slider.set_style_bg_color(
            lv_colors.GRAY_1, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.slider.set_style_bg_color(lv_colors.WHITE, lv.PART.KNOB | lv.STATE.DEFAULT)
        self.slider.set_style_bg_color(
            lv_colors.WHITE, lv.PART.INDICATOR | lv.STATE.DEFAULT
        )
        self.slider.add_event_cb(self.on_value_changed, lv.EVENT.VALUE_CHANGED, None)

    def on_value_changed(self, event_obj):
        target = event_obj.get_target()
        if target == self.slider:
            value = target.get_value()
            display.backlight(value)
            self.item1.label_right.set_text(brightness2_percent_str(value))
            device.set_brightness(value)


class PinMapSetting(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__PIN_KEYBOARD), nav_back=True
        )
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.random = ListItemBtn(
            self.container, _(i18n_keys.OPTION__RANDOMIZED), has_next=False
        )
        self.random.add_check_img()
        self.order = ListItemBtn(
            self.container, _(i18n_keys.OPTION__ORDERED), has_next=False
        )
        self.order.add_check_img()
        if device.is_order_pin_map_enabled():
            self.order.set_checked()
        else:
            self.random.set_checked()
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if utils.lcd_resume():
                return
            if target == self.random:
                self.random.set_checked()
                self.order.set_uncheck()
                if device.is_order_pin_map_enabled():
                    device.set_order_pin_map_enable(False)
            elif target == self.order:
                self.random.set_uncheck()
                self.order.set_checked()
                if not device.is_order_pin_map_enabled():
                    device.set_order_pin_map_enable(True)


class ConnectSetting(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__CONNECT), nav_back=True
        )
        self.container = ContainerFlexCol(self, self.title)
        self.ble = ListItemBtnWithSwitch(self.container, _(i18n_keys.ITEM__BLUETOOTH))
        self.ble.set_size(lv.pct(100), 78)
        from trezor import uart

        if uart.is_ble_opened():
            self.ble.add_state()
        else:
            self.ble.clear_state()
        # self.usb = ListItemBtnWithSwitch(self.container, _(i18n_keys.ITEM__USB))
        self.container.add_event_cb(self.on_value_changed, lv.EVENT.VALUE_CHANGED, None)

    def on_value_changed(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.VALUE_CHANGED:
            from trezor import uart

            if target == self.ble.switch:
                if target.has_state(lv.STATE.CHECKED):
                    uart.ctrl_ble(enable=True)
                else:
                    uart.ctrl_ble(enable=False)
            # else:
            #     if target.has_state(lv.STATE.CHECKED):
            #         print("USB is on")
            #     else:
            #         print("USB is off")


class AboutSetting(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        model = device.get_model()
        version = device.get_firmware_version()
        serial = device.get_serial()
        from trezor import uart

        ble_name = uart.get_ble_name()
        storage = device.get_storage()
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__ABOUT_DEVICE), nav_back=True
        )
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.model = ListItemBtn(
            self.container, _(i18n_keys.ITEM__MODEL), right_text=model, has_next=False
        )
        self.version = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__SYSTEM_VERSION),
            right_text=version,
            has_next=False,
        )
        self.serial = ListItemBtn(
            self.container, _(i18n_keys.ITEM__SERIAL), right_text=serial, has_next=False
        )
        self.ble_mac = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__BLUETOOTH),
            right_text=ble_name,
            has_next=False,
        )
        self.storage = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__STORAGE),
            right_text=storage,
            has_next=False,
        )
        self.storage = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__BUILD_ID),
            right_text=utils.BUILD_ID[-7:],
            has_next=False,
        )


class PowerOff(FullSizeWindow):
    def __init__(self, set_home: bool = False):
        super().__init__(
            title=_(i18n_keys.TITLE__POWER_OFF),
            subtitle=None,
            confirm_text=_(i18n_keys.ITEM__POWER_OFF),
            cancel_text=_(i18n_keys.BUTTON__CANCEL),
        )
        self.set_home = set_home
        self.btn_yes.enable(bg_color=lv_colors.ONEKEY_RED_1)
        from trezor import config

        self.has_pin = config.has_pin()
        if self.has_pin:
            config.lock()

    def eventhandler(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if utils.lcd_resume():
                return
            if target == self.btn_yes:
                self.destroy()
                ShutingDown()
            elif target == self.btn_no:
                self.destroy(500)
                if self.has_pin:
                    from apps.common.request_pin import verify_user_pin

                    workflow.spawn(
                        verify_user_pin(set_home=self.set_home, allow_cancel=False)
                    )


class ShutingDown(FullSizeWindow):
    def __init__(self):
        super().__init__(
            title=_(i18n_keys.TITLE__SHUTTING_DOWN), subtitle=None, top_layer=True
        )
        from trezor import loop, uart

        async def shutdown_delay():
            await loop.sleep(3000)
            uart.ctrl_power_off()

        self.destroy(3000)
        workflow.spawn(shutdown_delay())


class HomeScreenSetting(Screen):
    CELL_SIZE = 128

    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        cur_index = device.get_wp_index()
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__HOME_SCREEN), nav_back=True
        )
        # TODO: retrieve the total nums of wps, need fatfs interface to enumerate files
        pages_num = 5
        rows_num = math.ceil(pages_num / 3)
        row_dsc = [GRID_CELL_SIZE] * rows_num
        row_dsc.append(lv.GRID_TEMPLATE.LAST)
        # 3 columns
        col_dsc = [
            GRID_CELL_SIZE,
            GRID_CELL_SIZE,
            GRID_CELL_SIZE,
            lv.GRID_TEMPLATE.LAST,
        ]
        self.container = ContanierGrid(
            self, row_dsc=row_dsc, col_dsc=col_dsc, align_base=self.title
        )
        self.wps = []
        for i in range(pages_num):
            current_wp = ImgBottonGridItem(
                self.container, i % 3, i // 3, f"A:/res/zoom-{i+1}.png"
            )
            self.wps.append(current_wp)
            if cur_index == i:
                current_wp.set_checked(True)
        self.check_index = cur_index
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if utils.lcd_resume():
                return
            if target not in self.wps:
                return
            last_checked = self.check_index
            for idx, wp in enumerate(self.wps):
                if target != wp and idx == last_checked:
                    wp.set_checked(False)
                if target == wp and idx != last_checked:
                    device.set_cur_wp_index(idx)
                    self.check_index = idx
                    wp.set_checked(True)


class SecurityScreen(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(prev_scr, title=_(i18n_keys.TITLE__SECURITY), nav_back=True)
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.pin_map_type = ListItemBtn(self.container, _(i18n_keys.ITEM__PIN_KEYBOARD))
        self.usb_lock = ListItemBtn(self.container, _(i18n_keys.ITEM__USB_LOCK))
        self.change_pin = ListItemBtn(self.container, _(i18n_keys.ITEM__CHANGE_PIN))
        self.recovery_check = ListItemBtn(
            self.container, _(i18n_keys.ITEM__CHECK_RECOVERY_PHRASE)
        )
        # self.passphrase = ListItemBtn(self.container, _(i18n_keys.ITEM__PASSPHRASE))
        self.rest_device = ListItemBtn(
            self.container, _(i18n_keys.ITEM__RESET_DEVICE), has_next=False
        )
        self.rest_device.label_left.set_style_text_color(
            lv_colors.ONEKEY_RED_1, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        # pyright: off
        if code == lv.EVENT.CLICKED:
            from trezor.wire import DUMMY_CONTEXT

            if utils.lcd_resume():
                return
            if target == self.change_pin:
                from apps.management.change_pin import change_pin
                from trezor.messages import ChangePin

                workflow.spawn(change_pin(DUMMY_CONTEXT, ChangePin(remove=False)))
            elif target == self.recovery_check:
                from apps.management.recovery_device import recovery_device
                from trezor.messages import RecoveryDevice

                workflow.spawn(
                    recovery_device(
                        DUMMY_CONTEXT,
                        RecoveryDevice(dry_run=True, enforce_wordlist=True),
                    )
                )
            # elif target == self.passphrase:
            #     from apps.management.apply_settings import apply_settings
            #     from trezor.messages import ApplySettings

            #     passphrase_enable = not device.is_passphrase_enabled()
            #     if passphrase_enable:
            #         on_device = True
            #     else:
            #         on_device = None
            #     workflow.spawn(
            #         apply_settings(
            #             DUMMY_CONTEXT,
            #             ApplySettings(
            #                 use_passphrase=passphrase_enable,
            #                 passphrase_always_on_device=on_device,
            #             ),
            #         )
            #     )
            elif target == self.rest_device:
                from apps.management.wipe_device import wipe_device
                from trezor.messages import WipeDevice

                workflow.spawn(wipe_device(DUMMY_CONTEXT, WipeDevice()))
            elif target == self.pin_map_type:
                PinMapSetting(self)
            elif target == self.usb_lock:
                UsbLockSetting(self)
            else:
                if __debug__:
                    print("unknown")
        # pyright: on


class UsbLockSetting(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(
            prev_scr=prev_scr, title=_(i18n_keys.TITLE__USB_LOCK), nav_back=True
        )
        self.container = ContainerFlexCol(self, self.title)
        self.usb_lock = ListItemBtnWithSwitch(
            self.container, _(i18n_keys.ITEM__USB_LOCK)
        )
        self.usb_lock.set_size(lv.pct(100), 78)
        self.description = lv.label(self)
        self.description.set_size(416, lv.SIZE.CONTENT)
        self.description.set_long_mode(lv.label.LONG.WRAP)
        self.description.set_style_text_color(lv_colors.ONEKEY_GRAY, lv.STATE.DEFAULT)
        self.description.set_style_text_font(font_PJSREG24, lv.STATE.DEFAULT)
        self.description.set_style_text_line_space(6, lv.PART.MAIN | lv.STATE.DEFAULT)
        self.description.align_to(self.container, lv.ALIGN.OUT_BOTTOM_MID, 0, 20)

        if device.is_usb_lock_enabled():
            self.usb_lock.add_state()
            self.description.set_text(_(i18n_keys.CONTENT__USB_LOCK_ENABLED__HINT))
        else:
            self.usb_lock.clear_state()
            self.description.set_text(_(i18n_keys.CONTENT__USB_LOCK_DISABLED__HINT))
        self.container.add_event_cb(self.on_value_changed, lv.EVENT.VALUE_CHANGED, None)

    def on_value_changed(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.VALUE_CHANGED:
            if target == self.usb_lock.switch:
                if target.has_state(lv.STATE.CHECKED):
                    self.description.set_text(
                        _(i18n_keys.CONTENT__USB_LOCK_ENABLED__HINT)
                    )
                    device.set_usb_lock_enabled(True)
                else:
                    self.description.set_text(
                        _(i18n_keys.CONTENT__USB_LOCK_DISABLED__HINT)
                    )
                    device.set_usb_lock_enabled(False)


class CryptoScreen(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(prev_scr, title=_(i18n_keys.TITLE__CRYPTO), nav_back=True)
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.ethereum = ListItemBtn(self.container, _(i18n_keys.TITLE__ETHEREUM))
        self.solana = ListItemBtn(self.container, _(i18n_keys.TITLE__SOLANA))
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if target == self.ethereum:
                EthereumSetting(self)
            elif target == self.solana:
                SolanaSetting(self)


class EthereumSetting(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(prev_scr, title=_(i18n_keys.TITLE__ETHEREUM), nav_back=True)
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.blind_sign = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__BLIND_SIGNING),
            right_text=_(i18n_keys.ITEM__STATUS__OFF),
        )
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if target == self.blind_sign:
                BlindSign(self, coin_type=_(i18n_keys.TITLE__ETHEREUM))


class SolanaSetting(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        super().__init__(prev_scr, title=_(i18n_keys.TITLE__SOLANA), nav_back=True)
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.blind_sign = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__BLIND_SIGNING),
            right_text=_(i18n_keys.ITEM__STATUS__OFF),
        )
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if target == self.blind_sign:
                BlindSign(self, coin_type=_(i18n_keys.TITLE__SOLANA))


class BlindSign(Screen):
    def __init__(self, prev_scr=None, coin_type: str = _(i18n_keys.TITLE__ETHEREUM)):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            self.coin_type = coin_type
            return
        super().__init__(
            prev_scr, title=_(i18n_keys.TITLE__BLIND_SIGNING), nav_back=True
        )
        self.coin_type = coin_type
        self.container = ContainerFlexCol(self, self.title, padding_row=10)
        self.blind_sign = ListItemBtnWithSwitch(
            self.container, f"{coin_type} Blind Signing"
        )
        self.blind_sign.clear_state()
        self.container.add_event_cb(self.on_value_changed, lv.EVENT.VALUE_CHANGED, None)
        self.popup = None

    def on_value_changed(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.VALUE_CHANGED:
            if target == self.blind_sign.switch:
                if target.has_state(lv.STATE.CHECKED):
                    from .components.popup import Popup

                    self.popup = Popup(
                        self,
                        _(i18n_keys.TITLE__ENABLE_STR_BLIND_SIGNING).format(
                            self.coin_type
                        ),
                        _(i18n_keys.SUBTITLE_SETTING_CRYPTO_BLIND_SIGN_ENABLED),
                        icon_path="A:/res/warning.png",
                        btn_text=_(i18n_keys.BUTTON__ENABLE),
                    )
                else:
                    pass


class UserGuide(Screen):
    def __init__(self, prev_scr=None):
        if not hasattr(self, "_init"):
            self._init = True
        else:
            return
        kwargs = {
            "prev_scr": prev_scr,
            "title": _(i18n_keys.APP__USER_GUIDE),
            "nav_back": True,
        }
        super().__init__(**kwargs)
        self.container = ContainerFlexCol(self, self.title, padding_row=0)
        self.power_off = ListItemBtn(
            self.container,
            _(i18n_keys.TITLE__POWER_ON_OFF__GUIDE),
        )
        self.recovery_phrase = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__WHAT_IS_RECOVERY_PHRASE),
        )
        self.pin_protection = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__ENABLE_PIN_PROTECTION),
        )
        self.hardware_wallet = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__HOW_HARDWARE_WALLET_WORKS),
        )
        self.passphrase = ListItemBtn(
            self.container,
            _(i18n_keys.ITEM__PASSPHRASE_ACCESS_HIDDEN_WALLETS),
        )
        self.need_help = ListItemBtn(self.container, _(i18n_keys.ITEM__NEED_HELP))
        self.container.add_event_cb(self.on_click, lv.EVENT.CLICKED, None)

    def on_click(self, event_obj):
        code = event_obj.code
        target = event_obj.get_target()
        if code == lv.EVENT.CLICKED:
            if utils.lcd_resume():
                return
            if target == self.power_off:
                PowerOnOffDetails()
            elif target == self.recovery_phrase:
                RecoveryPhraseDetails()
            elif target == self.pin_protection:
                PinProtectionDetails()
            elif target == self.hardware_wallet:
                HardwareWalletDetails()
            elif target == self.passphrase:
                PassphraseDetails()
            elif target == self.need_help:
                HelpDetails()
            else:
                if __debug__:
                    print("Unknown")


class PowerOnOffDetails(FullSizeWindow):
    def __init__(self):
        super().__init__(
            None,
            None,
            cancel_text=_(i18n_keys.BUTTON__CLOSE),
            icon_path="A:/res/power-on-off.png",
        )
        self.container = ContainerFlexCol(self.content_area, self.icon, pos=(0, 24))
        self.item = DisplayItem(
            self.container,
            _(i18n_keys.TITLE__POWER_ON_OFF__GUIDE),
            _(i18n_keys.SUBTITLE__POWER_ON_OFF__GUIDE),
        )
        self.item.label_top.set_style_text_color(
            lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.set_style_text_color(
            lv_colors.WHITE_2, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.set_long_mode(lv.label.LONG.WRAP)

    def destroy(self):
        return self.delete()


class RecoveryPhraseDetails(FullSizeWindow):
    def __init__(self):
        super().__init__(
            None,
            None,
            cancel_text=_(i18n_keys.BUTTON__CLOSE),
            icon_path="A:/res/recovery-phrase.png",
        )
        self.container = ContainerFlexCol(self.content_area, self.icon, pos=(0, 24))
        self.item = DisplayItem(
            self.container,
            _(i18n_keys.TITLE__WHAT_IS_RECOVERY_PHRASE__GUIDE),
            _(i18n_keys.SUBTITLE__WHAT_IS_RECOVERY_PHRASE__GUIDE),
        )
        self.item.label_top.set_style_text_color(
            lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.set_style_text_color(
            lv_colors.WHITE_2, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.align_to(self.item.label_top, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 16)
        self.item.label.set_long_mode(lv.label.LONG.WRAP)

    def destroy(self):
        return self.delete()


class PinProtectionDetails(FullSizeWindow):
    def __init__(self):
        super().__init__(
            None,
            None,
            cancel_text=_(i18n_keys.BUTTON__CLOSE),
            icon_path="A:/res/pin-protection.png",
        )
        self.container = ContainerFlexCol(self.content_area, self.icon, pos=(0, 24))
        self.item = DisplayItem(
            self.container,
            _(i18n_keys.TITLE__ENABLE_PIN_PROTECTION__GUIDE),
            _(i18n_keys.SUBTITLE__ENABLE_PIN_PROTECTION__GUIDE),
        )
        self.item.label_top.set_style_text_color(
            lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.set_style_text_color(
            lv_colors.WHITE_2, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.align_to(self.item.label_top, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 16)
        self.item.label.set_long_mode(lv.label.LONG.WRAP)

    def destroy(self):
        return self.delete()


class HardwareWalletDetails(FullSizeWindow):
    def __init__(self):
        super().__init__(
            None,
            None,
            cancel_text=_(i18n_keys.BUTTON__CLOSE),
            icon_path="A:/res/hardware-wallet-works-way.png",
        )
        self.container = ContainerFlexCol(self.content_area, self.icon, pos=(0, 24))
        self.item = DisplayItem(
            self.container,
            _(i18n_keys.TITLE__HOW_HARDWARE_WALLET_WORKS__GUIDE),
            _(i18n_keys.SUBTITLE__HOW_HARDWARE_WALLET_WORKS__GUIDE),
        )
        self.item.label_top.set_style_text_color(
            lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.set_style_text_color(
            lv_colors.WHITE_2, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.align_to(self.item.label_top, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 16)
        self.item.label.set_long_mode(lv.label.LONG.WRAP)

    def destroy(self):
        return self.delete()


class PassphraseDetails(FullSizeWindow):
    def __init__(self):
        super().__init__(
            None,
            None,
            cancel_text=_(i18n_keys.BUTTON__CLOSE),
            icon_path="A:/res/hidden-wallet.png",
        )
        self.container = ContainerFlexCol(self.content_area, self.icon, pos=(0, 24))
        self.item = DisplayItem(
            self.container,
            _(i18n_keys.TITLE__ACCESS_HIDDEN_WALLET),
            _(i18n_keys.SUBTITLE__PASSPHRASE_ACCESS_HIDDEN_WALLETS__GUIDE),
        )
        self.item.label_top.set_style_text_color(
            lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.set_style_text_color(
            lv_colors.WHITE_2, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.align_to(self.item.label_top, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 16)
        self.item.label.set_long_mode(lv.label.LONG.WRAP)

    def destroy(self):
        return self.delete()


class HelpDetails(FullSizeWindow):
    def __init__(self):
        super().__init__(
            None,
            None,
            cancel_text=_(i18n_keys.BUTTON__CLOSE),
            icon_path="A:/res/onekey-help.png",
        )
        self.container = ContainerFlexCol(self.content_area, self.icon, pos=(0, 24))
        self.item = DisplayItem(
            self.container,
            _(i18n_keys.TITLE__NEED_HELP__GUIDE),
            _(i18n_keys.SUBTITLE__NEED_HELP__GUIDE),
        )
        self.item.label_top.set_style_text_color(
            lv_colors.WHITE, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.set_style_text_color(
            lv_colors.WHITE_2, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.item.label.set_long_mode(lv.label.LONG.WRAP)
        self.item.label.align_to(self.item.label_top, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 16)

        self.website = lv.label(self.content_area)
        self.website.set_style_text_font(font_PJSREG24, lv.PART.MAIN | lv.STATE.DEFAULT)
        self.website.set_style_text_color(
            lv_colors.WHITE_2, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.website.set_style_text_line_space(6, lv.PART.MAIN | lv.STATE.DEFAULT)
        self.website.set_text("help.onekey.so/hc")
        self.website.align_to(self.container, lv.ALIGN.OUT_BOTTOM_LEFT, 40, 0)
        self.underline = lv.line(self.content_area)
        self.underline.set_points(
            [
                {"x": 0, "y": 2},
                {"x": 232, "y": 2},
            ],
            2,
        )
        self.underline.set_style_line_color(
            lv_colors.WHITE_2, lv.PART.MAIN | lv.STATE.DEFAULT
        )
        self.underline.align_to(self.website, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 0)

    def destroy(self):
        return self.delete()
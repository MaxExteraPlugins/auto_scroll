__id__ = "auto_scroll"
__name__ = "Auto Scroll"
__description__ = "Автоматическая прокрутка сообщений в чатах.\n\nАктивация: (⋮) → Плагины → Auto Scroll в любом чате."
__author__ = "@itNotMax - @MaxExteraPlugins"
__icon__ = "MaxExteraPluginsStickers/17"
__version__ = "1.2.0"
__min_version__ = "12.10.6"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.3.3"

from typing import Any, Dict, List

from android.graphics import Color, PorterDuff, PorterDuffColorFilter, Typeface
from android.util import TypedValue
from android.view import Gravity, MotionEvent, View
from android.widget import FrameLayout, ImageView, LinearLayout, TextView

from android.os import Bundle

from org.telegram.messenger import AndroidUtilities, ChatObject, MessagesController, R as R_tg
from org.telegram.messenger.browser import Browser
from org.telegram.ui import ChatActivity

from base_plugin import BasePlugin, MenuItemData, MenuItemType
from android_utils import R, OnClickListener, run_on_ui_thread
from hook_utils import get_private_field
from client_utils import get_last_fragment
from ui.alert import AlertDialogBuilder
from ui.settings import Header, Text

from java import dynamic_proxy, jclass


def _c(color):
    if color > 0x7FFFFFFF:
        color -= 0x100000000
    return int(color)


COLOR_BG = _c(0xCC1B1B1B)
COLOR_STROKE = _c(0x33FFFFFF)
COLOR_DIVIDER = _c(0x33FFFFFF)
COLOR_BLUE = _c(0xFF64B5F6)
COLOR_RED = _c(0xFFFF6B6B)

DELAY_OPTIONS = [1, 2, 3, 5, 7, 10]
SCROLL_INTERVAL = 16
BOTTOM_PAUSE_TICKS = 30
WATCHER_INTERVAL = 500



# ============================================================
# MaxExteraPlugins Shared Author & Channel Subscription Module
# ============================================================

# ============================================================
# MaxExteraPlugins Shared Author & Channel Subscription Module
# ============================================================

# ============================================================
# MaxExteraPlugins Shared Author & Channel Subscription Module
# ============================================================

# ============================================================
# MaxExteraPlugins Shared Author & Channel Subscription Module
# ============================================================
class AuthorChannelHelper:
    CONFIG_URL = "https://raw.githubusercontent.com/MaxExteraPlugins/config/main/links.json"

    DEFAULT_LINKS = {
        "channel_username": "MaxExteraPlugins",
        "channel_url": "https://t.me/MaxExteraPlugins",
        "trial_days": 7,
        "header": {"ru": "MaxExteraPlugins", "en": "MaxExteraPlugins"},
        "buttons": [
            {"title": {"ru": "Канал автора", "en": "Author's Channel"}, "icon": "msg_channel", "url": "https://t.me/MaxExteraPlugins"},
            {"title": {"ru": "Поддержать автора", "en": "Support author"}, "icon": "msg_share", "url": "https://t.me/itNotMax"},
            {"title": {"ru": "Сообщить о баге", "en": "Report a bug"}, "icon": "msg_help", "url": "https://t.me/itNotMax"}
        ]
    }

    _TEXTS = {
        "install_card_title": {"ru": "Спасибо за установку!", "en": "Thank you for installing!"},
        "install_card_msg": {
            "ru": "Надеемся, что плагин будет вам полезен!\n\nМы делаем плагины бесплатными и доступными для всех: пожалуйста, поддержите нас подпиской. Там будут только важные новости, обновления и розыгрыши.",
            "en": "We hope this plugin will be useful to you!\n\nWe keep our plugins free and open for everyone: please support us with a subscription. We only post key news, updates, and giveaways."
        },
        "subscribe_btn": {"ru": "Подписаться", "en": "Subscribe"},
        "remind_later_btn": {"ru": "Напомнить позже", "en": "Remind later"},
        "check_sub_btn": {"ru": "Проверить подписку", "en": "Check subscription"},
        "trial_expired_title": {"ru": "Пожалуйста, подпишитесь на канал", "en": "Please subscribe to the channel"},
        "trial_expired_msg": {
            "ru": "Пожалуйста, подпишитесь на наш официальный канал.\n\nМы делаем плагины бесплатно, ничего не требуя взамен. До подписки функции плагина временно приостановлены.",
            "en": "Please subscribe to our official channel.\n\nWe develop plugins for free and ask nothing in return. Plugin features are paused until you subscribe."
        },
        "sub_thank_you": {"ru": "Спасибо за подписку на наш канал!", "en": "Thank you for subscribing to our channel!"},
        "sub_thank_you_after_expired": {"ru": "Спасибо за подписку на наш канал!\nПлагин продолжит работу!", "en": "Thank you for subscribing to our channel!\nThe plugin will continue working!"},
        "sub_not_found": {"ru": "Подписка не обнаружена. Пожалуйста, подпишитесь на канал.", "en": "Subscription not found. Please subscribe to the channel."},
        "settings_channel": {"ru": "Канал автора", "en": "Author's Channel"},
        "settings_donate": {"ru": "Поддержать автора", "en": "Support author"},
        "settings_bug_report": {"ru": "Сообщить о баге", "en": "Report a bug"}
    }

    @classmethod
    def is_ru(cls) -> bool:
        try:
            from org.telegram.messenger import LocaleController
            cur = str(LocaleController.getInstance().getCurrentLocale().getLanguage() or "").lower()
            if cur.startswith(("ru", "uk", "be")): return True
            if cur: return False
        except Exception:
            pass
        try:
            from java.util import Locale
            code = str(Locale.getDefault().getLanguage() or "").lower()
            if code.startswith(("ru", "uk", "be")): return True
        except Exception:
            pass
        return False

    @classmethod
    def tr(cls, key: str) -> str:
        entry = cls._TEXTS.get(key, {})
        return entry.get("ru" if cls.is_ru() else "en", entry.get("en", key))

    def __init__(self, plugin, icon_sticker=None):
        self.plugin = plugin
        self.icon_sticker = icon_sticker or getattr(plugin, "__icon__", "MaxExteraPluginsStickers/1")
        self._stopped = False
        self._active_dialog = None
        self._last_known_sub = None

    def on_load(self):
        self._stopped = False
        self._active_dialog = None
        self._last_known_sub = None
        self._load_remote_links_async()
        self._check_initial_subscription_flow()
        self._start_subscription_watcher()

    def on_event(self, event_type):
        try:
            name = str(event_type).upper()
            if name.endswith("START") or name.endswith("RESUME"):
                self._check_subscription_change_instant()
        except Exception:
            pass

    def on_unload(self):
        self._stopped = True
        self._dismiss_active_dialog()

    def _get_links(self) -> dict:
        raw = self.plugin.get_setting("remote_links_cache", None)
        if raw:
            try:
                import json
                data = json.loads(raw)
                if isinstance(data, dict): return data
            except Exception:
                pass
        return self.DEFAULT_LINKS

    def _load_remote_links_async(self):
        def worker():
            try:
                import urllib.request, json
                req = urllib.request.Request(self.CONFIG_URL, headers={"User-Agent": "MaxExteraPlugins"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        if isinstance(data, dict):
                            self.plugin.set_setting("remote_links_cache", json.dumps(data))
                            self._resolve_channel_in_telegram(data.get("channel_username", "MaxExteraPlugins"))
            except Exception:
                pass
        import threading
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _open_url(self, url: str, view=None):
        try:
            from org.telegram.messenger.browser import Browser
            from org.telegram.messenger import ApplicationLoader
            from client_utils import get_last_fragment
            ctx = None
            if view is not None:
                ctx = view.getContext()
            if ctx is None:
                frag = get_last_fragment()
                if frag is not None:
                    ctx = frag.getParentActivity()
            if ctx is None:
                ctx = ApplicationLoader.applicationContext
            Browser.openUrl(ctx, url)
        except Exception:
            pass

    def _resolve_channel_in_telegram(self, username: str):
        try:
            from org.telegram.messenger import UserConfig, MessagesController
            from org.telegram.tgnet import TLRPC, ConnectionsManager, RequestDelegate
            clean_user = username.lstrip("@")
            acc = int(UserConfig.selectedAccount)
            mc = MessagesController.getInstance(acc)
            if not mc: return
            req = TLRPC.TL_contacts_resolveUsername()
            req.username = clean_user
            helper_ref = self
            class Delegate(RequestDelegate):
                def run(self, response, error):
                    if error is None and response is not None:
                        chats = getattr(response, "chats", None)
                        if chats is not None and chats.size() > 0:
                            mc.putChats(chats, False)
                            c = chats.get(0)
                            cid = getattr(c, "id", 0)
                            if cid > 0:
                                helper_ref.plugin.set_setting("resolved_channel_id", int(cid))
            ConnectionsManager.getInstance(acc).sendRequest(req, Delegate())
        except Exception:
            pass

    def is_subscribed(self) -> bool:
        try:
            from org.telegram.messenger import UserConfig, MessagesController
            links = self._get_links()
            target = str(links.get("channel_username", "MaxExteraPlugins") or "MaxExteraPlugins").lower().lstrip("@")
            saved_cid = self.plugin.get_setting("resolved_channel_id", 0)

            for acc in range(UserConfig.MAX_ACCOUNT_COUNT):
                uconf = UserConfig.getInstance(acc)
                if not uconf.isClientActivated(): continue
                mc = MessagesController.getInstance(acc)
                if not mc: continue

                if saved_cid:
                    try:
                        from java.lang import Long as JLong
                        c = mc.getChat(JLong(int(saved_cid)))
                        if c is not None:
                            left = bool(getattr(c, "left", True))
                            kicked = bool(getattr(c, "kicked", False))
                            if not left and not kicked: return True
                    except Exception:
                        pass

                try:
                    chat = mc.getUserOrChat(target)
                    if chat is not None:
                        cid = getattr(chat, "id", 0)
                        if cid and not saved_cid:
                            self.plugin.set_setting("resolved_channel_id", int(cid))
                        left = bool(getattr(chat, "left", True))
                        kicked = bool(getattr(chat, "kicked", False))
                        if not left and not kicked: return True
                except Exception:
                    pass

                try:
                    dialogs = mc.allDialogs
                    if dialogs is not None:
                        limit = min(dialogs.size(), 300)
                        for i in range(limit):
                            d = dialogs.get(i)
                            did = getattr(d, "id", 0)
                            if did < 0:
                                from java.lang import Long as JLong
                                c = mc.getChat(JLong(-did))
                                if c is not None:
                                    uname = str(getattr(c, "username", "") or "").lower()
                                    if uname == target:
                                        cid = getattr(c, "id", 0)
                                        if cid and not saved_cid:
                                            self.plugin.set_setting("resolved_channel_id", int(cid))
                                        left = bool(getattr(c, "left", True))
                                        kicked = bool(getattr(c, "kicked", False))
                                        if not left and not kicked: return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    def is_allowed(self) -> bool:
        import time
        if self.is_subscribed():
            if not self.plugin.get_setting("was_subscribed", False):
                was_exp = bool(self.plugin.get_setting("was_expired_state", False))
                self.plugin.set_setting("was_subscribed", True)
                self.plugin.set_setting("was_expired_state", False)
                self._notify_subscribed(was_expired=was_exp)
            return True

        if self.plugin.get_setting("was_expired_state", False) or self.plugin.get_setting("was_subscribed", False):
            self.plugin.set_setting("was_subscribed", False)
            self.plugin.set_setting("was_expired_state", True)
            self._show_expired_card()
            return False

        now = time.time()
        install_time = float(self.plugin.get_setting("install_time", 0.0) or 0.0)
        if install_time <= 0:
            install_time = now
            self.plugin.set_setting("install_time", install_time)

        trial_days = float(self._get_links().get("trial_days", 7))
        trial_sec = trial_days * 86400.0

        if (now - install_time) < trial_sec:
            return True

        self.plugin.set_setting("was_expired_state", True)
        self._show_expired_card()
        return False

    def prepend_settings(self, original_items=None) -> list:
        from ui.settings import Header, Text, Divider

        # Prevent double-prepending
        if original_items and any(getattr(x, "text", "") == "MaxExteraPlugins" for x in original_items if type(x).__name__ == "Header"):
            return original_items

        links = self._get_links()
        buttons_config = links.get("buttons")

        author_items = []
        if isinstance(buttons_config, list):
            for btn in buttons_config:
                if not isinstance(btn, dict): continue
                raw_url = btn.get("url")
                if isinstance(raw_url, dict):
                    keys = [
                        getattr(self.plugin, "id", None),
                        globals().get("__id__", None),
                        globals().get("__name__", None),
                        self.plugin.__class__.__name__
                    ]
                    keys += [k.lower() for k in keys if isinstance(k, str)]
                    resolved_url = ""
                    for k in keys:
                        if k and k in raw_url:
                            resolved_url = str(raw_url[k] or "").strip()
                            if resolved_url:
                                break
                    url = resolved_url
                elif isinstance(raw_url, str):
                    url = raw_url.strip()
                else:
                    url = ""

                if not url: continue

                title_data = btn.get("title")
                if isinstance(title_data, dict):
                    title = title_data.get("ru" if self.is_ru() else "en") or title_data.get("en") or title_data.get("ru") or ""
                elif isinstance(title_data, str) and title_data:
                    title = title_data
                else:
                    title = btn.get("title_ru" if self.is_ru() else "title_en") or btn.get("title_ru") or btn.get("title_en") or ""

                if not title: continue
                icon = str(btn.get("icon") or "msg_channel").strip()

                def make_click(u):
                    return lambda v=None: self._open_url(u, v)

                author_items.append(Text(text=title, icon=icon, on_click=make_click(url)))
        else:
            for k, text_key, icon_name in [
                ("channel_url", "settings_channel", "msg_channel"),
                ("donate_url", "settings_donate", "msg_share"),
                ("bug_report_url", "settings_bug_report", "msg_help")
            ]:
                u = str(links.get(k) or "").strip()
                if u:
                    author_items.append(Text(text=self.tr(text_key), icon=icon_name, on_click=lambda v=None, target_u=u: self._open_url(target_u, v)))

        res = []
        if author_items:
            hdr = links.get("header") or "MaxExteraPlugins"
            if isinstance(hdr, dict):
                hdr_text = hdr.get("ru" if self.is_ru() else "en") or hdr.get("ru") or hdr.get("en") or "MaxExteraPlugins"
            else:
                hdr_text = str(hdr)
            res.append(Header(text=hdr_text))
            res.extend(author_items)
            res.append(Divider())

        # Clean original_items by removing any old "Информация" / "Information" category
        cleaned_items = []
        if original_items:
            skipping_info = False
            for item in original_items:
                item_cls = type(item).__name__
                if item_cls == "Header":
                    txt = str(getattr(item, "text", "") or getattr(item, "title", "") or "").lower()
                    if "информ" in txt or "inform" in txt:
                        skipping_info = True
                        continue
                    else:
                        skipping_info = False
                elif skipping_info and item_cls == "Divider":
                    skipping_info = False
                    continue

                if not skipping_info:
                    cleaned_items.append(item)

        res.extend(cleaned_items)
        return res

    def _dismiss_active_dialog(self):
        try:
            if self._active_dialog is not None:
                self._active_dialog.dismiss()
        except Exception:
            pass
        self._active_dialog = None

    def _is_dialog_active(self) -> bool:
        try:
            if self._active_dialog is not None:
                return bool(self._active_dialog.isShowing())
        except Exception:
            pass
        return False

    def _notify_subscribed(self, was_expired=False):
        self.plugin.set_setting("was_subscribed", True)
        from ui.bulletin import BulletinHelper
        msg_key = "sub_thank_you_after_expired" if was_expired else "sub_thank_you"
        BulletinHelper.show_success(self.tr(msg_key))

    def _check_subscription_change_instant(self):
        try:
            from android_utils import run_on_ui_thread
            cur_sub = self.is_subscribed()
            prev_sub = self._last_known_sub
            if prev_sub is not None and prev_sub != cur_sub:
                self._last_known_sub = cur_sub
                if cur_sub:
                    was_exp = bool(self.plugin.get_setting("was_expired_state", False))
                    self.plugin.set_setting("was_subscribed", True)
                    self.plugin.set_setting("was_expired_state", False)
                    self._dismiss_active_dialog()
                    self._notify_subscribed(was_expired=was_exp)
                else:
                    self.plugin.set_setting("was_subscribed", False)
                    self.plugin.set_setting("was_expired_state", True)
                    self._dismiss_active_dialog()
                    self._show_expired_card()
            else:
                self._last_known_sub = cur_sub
        except Exception:
            pass

    def _start_subscription_watcher(self):
        def watcher_loop():
            import time
            from android_utils import run_on_ui_thread
            time.sleep(2.0)
            if self._stopped: return
            self._last_known_sub = self.is_subscribed()

            while not self._stopped:
                try:
                    time.sleep(2.0)
                    if self._stopped: break
                    cur_sub = self.is_subscribed()
                    prev_sub = self._last_known_sub

                    if prev_sub is not None and prev_sub != cur_sub:
                        self._last_known_sub = cur_sub
                        if cur_sub:
                            was_exp = bool(self.plugin.get_setting("was_expired_state", False))
                            self.plugin.set_setting("was_subscribed", True)
                            self.plugin.set_setting("was_expired_state", False)
                            def on_sub():
                                self._dismiss_active_dialog()
                                self._notify_subscribed(was_expired=was_exp)
                            run_on_ui_thread(on_sub)
                        else:
                            self.plugin.set_setting("was_subscribed", False)
                            self.plugin.set_setting("was_expired_state", True)
                            def on_unsub():
                                self._dismiss_active_dialog()
                                self._show_expired_card()
                            run_on_ui_thread(on_unsub)
                    else:
                        self._last_known_sub = cur_sub
                except Exception:
                    pass
        import threading
        t = threading.Thread(target=watcher_loop, daemon=True)
        t.start()

    def _check_initial_subscription_flow(self):
        def flow():
            import time
            try:
                now = time.time()
                install_time = float(self.plugin.get_setting("install_time", 0.0) or 0.0)
                if install_time <= 0:
                    install_time = now
                    self.plugin.set_setting("install_time", install_time)

                is_sub = self.is_subscribed()
                self._last_known_sub = is_sub
                was_sub = bool(self.plugin.get_setting("was_subscribed", False))
                was_exp = bool(self.plugin.get_setting("was_expired_state", False))

                if is_sub:
                    if not was_sub:
                        self.plugin.set_setting("was_subscribed", True)
                        self.plugin.set_setting("was_expired_state", False)
                        self._notify_subscribed(was_expired=was_exp)
                    return

                if was_sub or was_exp:
                    self.plugin.set_setting("was_subscribed", False)
                    self.plugin.set_setting("was_expired_state", True)
                    self._show_expired_card()
                    return

                trial_days = float(self._get_links().get("trial_days", 7))
                trial_sec = trial_days * 86400.0
                last_remind = float(self.plugin.get_setting("last_remind_time", 0.0) or 0.0)

                if (now - install_time) < trial_sec:
                    if last_remind <= 0 or (now - last_remind) >= trial_sec:
                        self._show_welcome_card()
                else:
                    self.plugin.set_setting("was_expired_state", True)
                    self._show_expired_card()
            except Exception:
                pass
        from android_utils import run_on_ui_thread
        run_on_ui_thread(flow, 1500)

    def _create_card_content(self, act, title_text, message_text):
        try:
            from android.widget import LinearLayout, TextView
            from android.view import Gravity
            from android.graphics import Typeface
            from org.telegram.messenger import AndroidUtilities, UserConfig, MediaDataController
            from org.telegram.ui.ActionBar import Theme
            from org.telegram.ui.Components import BackupImageView

            dp = AndroidUtilities.dp
            layout = LinearLayout(act)
            layout.setOrientation(LinearLayout.VERTICAL)
            layout.setGravity(Gravity.CENTER_HORIZONTAL)
            layout.setPadding(dp(24), dp(16), dp(24), dp(6))

            size = dp(76)
            iv = BackupImageView(act)
            iv.setRoundRadius(dp(18))
            lp_iv = LinearLayout.LayoutParams(size, size)
            lp_iv.gravity = Gravity.CENTER_HORIZONTAL
            lp_iv.setMargins(0, dp(4), 0, dp(16))
            iv.setLayoutParams(lp_iv)

            try:
                acc = int(UserConfig.selectedAccount)
                mdc = MediaDataController.getInstance(acc)
                raw_icon = str(self.icon_sticker)
                if "/" in raw_icon:
                    pack, idx_s = raw_icon.split("/", 1)
                    mdc.setPlaceholderImageByIndex(iv, pack, int(idx_s), "150_150")
            except Exception:
                pass
            layout.addView(iv)

            if title_text:
                tt = TextView(act)
                tt.setText(title_text)
                tt.setTextSize(19.0)
                tt.setTypeface(None, Typeface.BOLD)
                tt.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
                tt.setGravity(Gravity.CENTER_HORIZONTAL)
                lp_t = LinearLayout.LayoutParams(-1, -2)
                lp_t.setMargins(0, 0, 0, dp(12))
                tt.setLayoutParams(lp_t)
                layout.addView(tt)

            if message_text:
                mt = TextView(act)
                mt.setText(message_text)
                mt.setTextSize(15.0)
                mt.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
                mt.setLineSpacing(float(dp(3)), 1.0)
                mt.setGravity(Gravity.CENTER_HORIZONTAL)
                lp_m = LinearLayout.LayoutParams(-1, -2)
                mt.setLayoutParams(lp_m)
                layout.addView(mt)

            return layout
        except Exception:
            return None

    def _show_welcome_card(self):
        def show():
            try:
                if self._is_dialog_active(): return
                from client_utils import get_last_fragment
                frag = get_last_fragment()
                if not frag: return
                act = frag.getParentActivity()
                if not act: return

                links = self._get_links()
                url = links.get("channel_url", "https://t.me/MaxExteraPlugins")

                from ui.alert import AlertDialogBuilder
                b = AlertDialogBuilder(act)
                content = self._create_card_content(act, self.tr("install_card_title"), self.tr("install_card_msg"))
                if content is not None:
                    b.set_view(content)
                else:
                    b.set_title(self.tr("install_card_title"))
                    b.set_message(self.tr("install_card_msg"))

                def on_sub(d, w):
                    self._dismiss_active_dialog()
                    self._open_url(url)
                    def check_after():
                        if self.is_subscribed():
                            self._notify_subscribed(was_expired=False)
                    from android_utils import run_on_ui_thread
                    run_on_ui_thread(check_after, 3000)

                def on_later(d, w):
                    import time
                    self._dismiss_active_dialog()
                    self.plugin.set_setting("last_remind_time", time.time())

                b.set_positive_button(self.tr("subscribe_btn"), on_sub)
                b.set_negative_button(self.tr("remind_later_btn"), on_later)
                self._active_dialog = b.show()
            except Exception:
                pass
        from android_utils import run_on_ui_thread
        run_on_ui_thread(show)

    def _show_expired_card(self):
        def show():
            try:
                if self._is_dialog_active(): return
                from client_utils import get_last_fragment
                frag = get_last_fragment()
                if not frag: return
                act = frag.getParentActivity()
                if not act: return

                links = self._get_links()
                url = links.get("channel_url", "https://t.me/MaxExteraPlugins")

                from ui.alert import AlertDialogBuilder
                from ui.bulletin import BulletinHelper
                b = AlertDialogBuilder(act)
                content = self._create_card_content(act, self.tr("trial_expired_title"), self.tr("trial_expired_msg"))
                if content is not None:
                    b.set_view(content)
                else:
                    b.set_title(self.tr("trial_expired_title"))
                    b.set_message(self.tr("trial_expired_msg"))

                def on_sub(d, w):
                    self._dismiss_active_dialog()
                    self._open_url(url)
                    def check_after():
                        if self.is_subscribed():
                            self.plugin.set_setting("was_subscribed", True)
                            self.plugin.set_setting("was_expired_state", False)
                            self._notify_subscribed(was_expired=True)
                    from android_utils import run_on_ui_thread
                    run_on_ui_thread(check_after, 3000)

                def on_check(d, w):
                    self._dismiss_active_dialog()
                    if self.is_subscribed():
                        self.plugin.set_setting("was_subscribed", True)
                        self.plugin.set_setting("was_expired_state", False)
                        self._notify_subscribed(was_expired=True)
                    else:
                        BulletinHelper.show_error(self.tr("sub_not_found"))
                        from android_utils import run_on_ui_thread
                        run_on_ui_thread(self._show_expired_card, 500)

                b.set_positive_button(self.tr("subscribe_btn"), on_sub)
                b.set_negative_button(self.tr("check_sub_btn"), on_check)
                self._active_dialog = b.show()
            except Exception:
                pass
        from android_utils import run_on_ui_thread
        run_on_ui_thread(show)


class AutoScrollPlugin(BasePlugin):
    def on_app_event(self, event_type):
        if hasattr(self, "_author_helper"):
            self._author_helper.on_event(event_type)

    def on_plugin_load(self):
        self._author_helper = AuthorChannelHelper(self, icon_sticker="MaxExteraPluginsStickers/17")
        self._author_helper.on_load()
        self._overlay = None
        self._overlay_parent = None
        self._scrolling = False
        self._speed = 3
        self._direction = 1
        self._runnable = None
        self._chat_list_view = None
        self._fragment = None
        self._speed_label = None
        self._btn_play = None
        self._btn_up = None
        self._btn_down = None
        self._touch_held = False
        self._touch_listener = None
        self._end_reached_count = 0
        self._active = False
        self._panel = None
        self._watcher = None
        self._last_fragment_id = None

        if self.get_setting("remember_speed", False):
            saved = self.get_setting("last_speed", 3)
            if isinstance(saved, int) and 1 <= saved <= 30:
                self._speed = saved

        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.CHAT_ACTION_MENU,
                text="Auto Scroll",
                on_click=self._on_menu_click,
                icon="msg_autodelete",
                item_id="auto_scroll_toggle",
            )
        )

    def _open_url(self, url):
        try:
            frag = get_last_fragment()
            if frag is not None:
                activity = frag.getParentActivity()
                if activity is not None:
                    Browser.openUrl(activity, url)
        except Exception:
            pass

    def create_settings(self):
        try:
            items = self._inner_create_settings()
        except Exception:
            items = []
        if hasattr(self, '_author_helper'):
            return self._author_helper.prepend_settings(items)
        return items

    def _inner_create_settings(self):
        return [
            Header(text="Информация"),
            Text(
                text="Документация",
                subtext="Как пользоваться плагином",
                icon="msg_help",
                on_click=lambda v: self._open_url("https://telegra.ph/Dokumentaciya-k-plaginu-Auto-Scroll-06-24"),
            ),
            Text(
                text="Канал автора",
                subtext="@MaxExteraPlugins",
                icon="msg_channel",
                on_click=lambda v: self._open_url("https://t.me/MaxExteraPlugins"),
            ),
        ]

    def on_plugin_unload(self):
        if hasattr(self, "_author_helper"):
            self._author_helper.on_unload()
        self._active = False
        self._stop_scroll()
        self._stop_watcher()
        self._remove_overlay()

    def _on_menu_click(self, context: Dict[str, Any]):
        fragment = context.get("fragment")
        if not isinstance(fragment, ChatActivity):
            return
        if self._active:
            self._active = False
            self._stop_scroll()
            self._stop_watcher()
            self._remove_overlay()
            return
        self._active = True
        self._fragment = fragment
        self._last_fragment_id = id(fragment)
        run_on_ui_thread(lambda: self._show_overlay(fragment, auto_start=True))

    def _start_watcher(self):
        self._stop_watcher()
        if not self._active:
            return

        def check():
            if not self._active:
                return
            try:
                frag = get_last_fragment()
                if isinstance(frag, ChatActivity):
                    frag_id = id(frag)
                    if frag_id != self._last_fragment_id:
                        self._last_fragment_id = frag_id
                        self._stop_scroll()
                        self._detach_touch_listener()
                        self._remove_overlay_view()
                        run_on_ui_thread(lambda f=frag: self._show_overlay(f, auto_start=False))
            except Exception:
                pass
            if self._active:
                w = R(check)
                self._watcher = w
                AndroidUtilities.runOnUIThread(w, WATCHER_INTERVAL)

        w = R(check)
        self._watcher = w
        AndroidUtilities.runOnUIThread(w, WATCHER_INTERVAL)

    def _stop_watcher(self):
        if self._watcher is not None:
            try:
                AndroidUtilities.cancelRunOnUIThread(self._watcher)
            except Exception:
                pass
            self._watcher = None

    def _get_nav_delay_ticks(self):
        secs = self.get_setting("nav_delay", 3)
        if not isinstance(secs, int) or secs < 1:
            secs = 3
        return int(secs * 1000 / SCROLL_INTERVAL)

    def _show_overlay(self, fragment, auto_start=True):
        try:
            ctx = fragment.getParentActivity()
            if ctx is None:
                return

            content_view = fragment.getFragmentView()
            if content_view is None:
                return

            chat_list = None
            try:
                chat_list = fragment.getChatListView()
            except Exception:
                pass
            if chat_list is None:
                chat_list = get_private_field(fragment, "chatListView")
            if chat_list is None:
                return
            self._chat_list_view = chat_list
            self._fragment = fragment
            self._last_fragment_id = id(fragment)
            self._end_reached_count = 0
            self._attach_touch_listener(chat_list)

            container = FrameLayout(ctx)
            container.setClickable(False)
            container.setFocusable(False)

            panel = LinearLayout(ctx)
            panel.setOrientation(LinearLayout.HORIZONTAL)
            panel.setGravity(Gravity.CENTER_VERTICAL)
            panel.setPadding(
                AndroidUtilities.dp(14),
                AndroidUtilities.dp(8),
                AndroidUtilities.dp(14),
                AndroidUtilities.dp(8),
            )

            bg = jclass("android.graphics.drawable.GradientDrawable")()
            bg.setShape(0)
            bg.setCornerRadius(float(AndroidUtilities.dp(28)))
            bg.setColor(COLOR_BG)
            bg.setStroke(AndroidUtilities.dp(1), COLOR_STROKE)
            panel.setBackground(bg)
            panel.setElevation(float(AndroidUtilities.dp(6)))
            self._panel = panel

            btn_play = self._make_text_button(ctx, "▶", self._on_play_click)
            self._btn_play = btn_play
            panel.addView(btn_play, self._btn_lp())

            divider1 = self._make_divider(ctx)
            panel.addView(divider1)

            btn_up = self._make_text_button(ctx, "▲", self._on_up_click)
            self._btn_up = btn_up
            panel.addView(btn_up, self._btn_lp())

            btn_down = self._make_text_button(ctx, "▼", self._on_down_click)
            self._btn_down = btn_down
            panel.addView(btn_down, self._btn_lp())

            self._highlight_direction()

            divider2 = self._make_divider(ctx)
            panel.addView(divider2)

            btn_minus = self._make_text_button(ctx, "−", self._on_minus_click)
            panel.addView(btn_minus, self._btn_lp())

            speed_label = TextView(ctx)
            speed_label.setText(str(self._speed))
            speed_label.setTextColor(Color.WHITE)
            speed_label.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
            speed_label.setTypeface(Typeface.DEFAULT_BOLD)
            speed_label.setGravity(Gravity.CENTER)
            speed_label.setMinWidth(AndroidUtilities.dp(24))
            self._speed_label = speed_label
            panel.addView(speed_label, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            ))

            btn_plus = self._make_text_button(ctx, "+", self._on_plus_click)
            panel.addView(btn_plus, self._btn_lp())

            divider3 = self._make_divider(ctx)
            panel.addView(divider3)

            btn_settings = self._make_text_button(ctx, "⚙", self._on_settings_click)
            panel.addView(btn_settings, self._btn_lp())

            divider4 = self._make_divider(ctx)
            panel.addView(divider4)

            btn_close = self._make_text_button(ctx, "✕", self._on_close_click)
            btn_close.setTextColor(COLOR_RED)
            panel.addView(btn_close, self._btn_lp())

            fl_params = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
            )
            fl_params.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL
            fl_params.topMargin = AndroidUtilities.dp(8)
            container.addView(panel, fl_params)

            overlay_params = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT,
            )

            parent = content_view
            if isinstance(parent, FrameLayout):
                parent.addView(container, overlay_params)
            else:
                p = parent.getParent()
                while p is not None:
                    if isinstance(p, FrameLayout):
                        parent = p
                        break
                    try:
                        p = p.getParent()
                    except Exception:
                        break
                if isinstance(parent, FrameLayout):
                    parent.addView(container, overlay_params)
                else:
                    return

            self._overlay = container
            self._overlay_parent = parent

            self._scrolling = auto_start
            self._update_play_button()
            if auto_start:
                self._start_scroll()

            self._start_watcher()
        except Exception as e:
            self.log(f"AutoScroll overlay error: {e}")

    def _attach_touch_listener(self, chat_list):
        plugin = self

        class ScrollTouchListener(dynamic_proxy(View.OnTouchListener)):
            def onTouch(self, v, event):
                action = event.getActionMasked()
                if action == MotionEvent.ACTION_DOWN:
                    plugin._touch_held = True
                    plugin._cancel_runnable()
                elif action == MotionEvent.ACTION_UP or action == MotionEvent.ACTION_CANCEL:
                    plugin._touch_held = False
                    if plugin._scrolling:
                        plugin._start_scroll()
                return False

        self._touch_listener = ScrollTouchListener()
        chat_list.setOnTouchListener(self._touch_listener)

    def _detach_touch_listener(self):
        if self._chat_list_view is not None:
            try:
                self._chat_list_view.setOnTouchListener(None)
            except Exception:
                pass
        self._touch_listener = None
        self._touch_held = False

    def _make_text_button(self, ctx, text, callback):
        tv = TextView(ctx)
        tv.setText(text)
        tv.setTextColor(Color.WHITE)
        tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 17)
        tv.setTypeface(Typeface.DEFAULT_BOLD)
        tv.setGravity(Gravity.CENTER)
        tv.setMinWidth(AndroidUtilities.dp(32))
        tv.setMinHeight(AndroidUtilities.dp(32))
        tv.setOnClickListener(OnClickListener(lambda v: callback()))
        return tv

    def _make_divider(self, ctx):
        d = View(ctx)
        d.setBackgroundColor(COLOR_DIVIDER)
        lp = LinearLayout.LayoutParams(AndroidUtilities.dp(1), AndroidUtilities.dp(20))
        lp.leftMargin = AndroidUtilities.dp(4)
        lp.rightMargin = AndroidUtilities.dp(4)
        d.setLayoutParams(lp)
        return d

    def _btn_lp(self):
        lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            AndroidUtilities.dp(32),
        )
        return lp

    def _on_play_click(self):
        self._scrolling = not self._scrolling
        self._update_play_button()
        if self._scrolling:
            self._end_reached_count = 0
            self._start_scroll()
        else:
            self._stop_scroll()

    def _on_up_click(self):
        self._direction = -1
        self._highlight_direction()

    def _on_down_click(self):
        self._direction = 1
        self._highlight_direction()

    def _highlight_direction(self):
        if self._btn_up is not None and self._btn_down is not None:
            if self._direction == -1:
                self._btn_up.setTextColor(COLOR_BLUE)
                self._btn_down.setTextColor(Color.WHITE)
            else:
                self._btn_up.setTextColor(Color.WHITE)
                self._btn_down.setTextColor(COLOR_BLUE)

    def _on_settings_click(self):
        run_on_ui_thread(lambda: self._show_settings_dialog())

    def _show_settings_dialog(self):
        fragment = self._fragment
        if fragment is None:
            return
        activity = fragment.getParentActivity()
        if activity is None:
            return

        remember = self.get_setting("remember_speed", False)
        auto_nav = self.get_setting("auto_navigate", False)
        nav_delay = self.get_setting("nav_delay", 3)

        items = [
            ("☑" if remember else "☐") + "  Запоминать скорость",
            ("☑" if auto_nav else "☐") + "  Авто-переход к следующему чату",
            "Задержка перед переходом: " + str(nav_delay) + " сек",
        ]

        plugin = self

        def on_click(bld, which):
            if which == 0:
                new_val = not remember
                plugin.set_setting("remember_speed", new_val)
                if new_val:
                    plugin.set_setting("last_speed", plugin._speed)
                bld.dismiss()
                run_on_ui_thread(lambda: plugin._show_settings_dialog())
            elif which == 1:
                plugin.set_setting("auto_navigate", not auto_nav)
                bld.dismiss()
                run_on_ui_thread(lambda: plugin._show_settings_dialog())
            elif which == 2:
                bld.dismiss()
                run_on_ui_thread(lambda: plugin._show_delay_picker(activity))

        builder = AlertDialogBuilder(activity)
        builder.set_title("Auto Scroll")
        builder.set_items(items, on_click)
        builder.set_negative_button("Закрыть", lambda b, w: b.dismiss())
        builder.show()

    def _show_delay_picker(self, activity):
        current = self.get_setting("nav_delay", 3)
        items = [("● " if d == current else "○ ") + str(d) + " сек" for d in DELAY_OPTIONS]
        plugin = self

        def on_pick(bld, which):
            plugin.set_setting("nav_delay", DELAY_OPTIONS[which])
            bld.dismiss()
            run_on_ui_thread(lambda: plugin._show_settings_dialog())

        builder = AlertDialogBuilder(activity)
        builder.set_title("Задержка перехода")
        builder.set_items(items, on_pick)
        builder.set_negative_button("Отмена", lambda b, w: (b.dismiss(), run_on_ui_thread(lambda: plugin._show_settings_dialog())))
        builder.show()

    def _save_speed(self):
        if self.get_setting("remember_speed", False):
            self.set_setting("last_speed", self._speed)

    def _on_minus_click(self):
        if self._speed > 1:
            self._speed -= 1
            self._update_speed_label()
            self._save_speed()

    def _on_plus_click(self):
        if self._speed < 30:
            self._speed += 1
            self._update_speed_label()
            self._save_speed()

    def _update_speed_label(self):
        if self._speed_label is not None:
            run_on_ui_thread(lambda: self._speed_label.setText(str(self._speed)))

    def _on_close_click(self):
        self._active = False
        self._stop_scroll()
        self._stop_watcher()
        self._remove_overlay()

    def _update_play_button(self):
        if self._btn_play is None:
            return
        if self._scrolling:
            self._btn_play.setText("⏸")
        else:
            self._btn_play.setText("▶")

    def _start_scroll(self):
        self._cancel_runnable()
        if not self._scrolling or self._touch_held:
            return

        def do_scroll():
            if not self._scrolling or self._chat_list_view is None:
                return
            can_scroll = True
            try:
                can_scroll = self._chat_list_view.canScrollVertically(self._direction)
            except Exception:
                pass
            if can_scroll:
                self._end_reached_count = 0
                try:
                    pixels = self._speed * 3 * self._direction
                    self._chat_list_view.smoothScrollBy(0, pixels, None)
                except Exception:
                    try:
                        pixels = self._speed * 3 * self._direction
                        self._chat_list_view.smoothScrollBy(0, pixels)
                    except Exception:
                        self._scrolling = False
                        run_on_ui_thread(lambda: self._update_play_button())
                        return
            else:
                self._end_reached_count += 1
                auto_nav = self.get_setting("auto_navigate", False)
                if auto_nav and self._end_reached_count > self._get_nav_delay_ticks():
                    self._end_reached_count = 0
                    run_on_ui_thread(lambda: self._navigate_to_next())
                    return
                if not auto_nav and self._end_reached_count > BOTTOM_PAUSE_TICKS:
                    self._end_reached_count = 0
                    self._scrolling = False
                    run_on_ui_thread(lambda: self._update_play_button())
                    return
            if self._scrolling:
                r = R(do_scroll)
                self._runnable = r
                AndroidUtilities.runOnUIThread(r, SCROLL_INTERVAL)

        r = R(do_scroll)
        self._runnable = r
        AndroidUtilities.runOnUIThread(r, SCROLL_INTERVAL)

    def _navigate_to_next(self):
        fragment = self._fragment
        if fragment is None:
            return
        try:
            current_chat = get_private_field(fragment, "currentChat")
            if current_chat is None:
                self._scrolling = False
                self._update_play_button()
                return
            is_channel = ChatObject.isChannel(current_chat)
            is_forum = False
            try:
                is_forum = bool(current_chat.forum)
            except Exception:
                pass
            if not is_channel and not is_forum:
                self._end_reached_count = 0
                self._scrolling = False
                self._update_play_button()
                return

            current_dialog_id = get_private_field(fragment, "dialog_id")
            account = fragment.getCurrentAccount()
            controller = MessagesController.getInstance(account)
            dialogs = controller.allDialogs

            next_id = self._find_next_unread(dialogs, current_dialog_id, controller)
            if next_id is None:
                self._end_reached_count = 0
                self._scrolling = False
                self._update_play_button()
                return

            self._cancel_runnable()
            self._detach_touch_listener()
            self._remove_overlay_view()

            args = Bundle()
            if next_id < 0:
                args.putLong("chat_id", -next_id)
            else:
                args.putLong("user_id", next_id)
            new_frag = ChatActivity(args)
            fragment.presentFragment(new_frag, True)

            self._last_fragment_id = id(new_frag)

            def reattach():
                if not self._active:
                    return
                self._show_overlay(new_frag, auto_start=True)

            run_on_ui_thread(reattach, 500)
        except Exception as e:
            self.log(f"AutoScroll navigate error: {e}")

    def _find_next_unread(self, dialogs, current_dialog_id, controller):
        found = False
        for i in range(dialogs.size()):
            d = dialogs.get(i)
            if d.id == current_dialog_id:
                found = True
                continue
            if found and d.unread_count > 0 and d.id < 0:
                chat = controller.getChat(int(-d.id))
                if chat is not None:
                    is_ch = ChatObject.isChannel(chat)
                    is_f = False
                    try:
                        is_f = bool(chat.forum)
                    except Exception:
                        pass
                    if is_ch or is_f:
                        return d.id
        for i in range(dialogs.size()):
            d = dialogs.get(i)
            if d.id == current_dialog_id:
                return None
            if d.unread_count > 0 and d.id < 0:
                chat = controller.getChat(int(-d.id))
                if chat is not None:
                    is_ch = ChatObject.isChannel(chat)
                    is_f = False
                    try:
                        is_f = bool(chat.forum)
                    except Exception:
                        pass
                    if is_ch or is_f:
                        return d.id
        return None

    def _stop_scroll(self):
        self._scrolling = False
        self._cancel_runnable()
        if self._btn_play is not None:
            self._update_play_button()

    def _cancel_runnable(self):
        if self._runnable is not None:
            try:
                AndroidUtilities.cancelRunOnUIThread(self._runnable)
            except Exception:
                pass
            self._runnable = None

    def _remove_overlay(self):
        self._detach_touch_listener()
        self._remove_overlay_view()
        self._fragment = None

    def _remove_overlay_view(self):
        if self._overlay is not None:
            try:
                parent = self._overlay.getParent()
                if parent is not None:
                    parent.removeView(self._overlay)
            except Exception:
                pass
            self._overlay = None
            self._overlay_parent = None
            self._panel = None
            self._btn_play = None
            self._btn_up = None
            self._btn_down = None
            self._speed_label = None
            self._chat_list_view = None

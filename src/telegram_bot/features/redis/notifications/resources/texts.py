from typing import cast

from aiogram_i18n import I18nContext


class NotificationsTexts:
    """
    Text wrappers for the Redis Notifications feature.
    All user-visible texts are served via i18n FTL files.
    FTL keys are in: resources/locales/{lang}/notifications.ftl
    """

    @staticmethod
    def get_i18n():
        return cast("I18nContext", I18nContext.get_current())

    @classmethod
    def new_event(cls):
        return cls.get_i18n().notifications.new.event()

    @classmethod
    def btn_approve(cls):
        return cls.get_i18n().notifications.btn.approve()

    @classmethod
    def btn_reject(cls):
        return cls.get_i18n().notifications.btn.reject()

    @classmethod
    def btn_delete(cls):
        return cls.get_i18n().notifications.btn.delete()

    @classmethod
    def reason_busy(cls):
        return cls.get_i18n().notifications.reason.busy()

    @classmethod
    def reason_other(cls):
        return cls.get_i18n().notifications.reason.other()

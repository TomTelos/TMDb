from Tools.Directories import resolveFilename, SCOPE_PLUGINS

PluginName = 'tmdb'
PluginGroup = 'Extensions'
PluginFolder = PluginName
PluginPath = resolveFilename(SCOPE_PLUGINS, '%s/%s/' %(PluginGroup,PluginFolder))
PluginLanguageDomain = "plugin-" + PluginName
PluginLanguagePath = resolveFilename(SCOPE_PLUGINS, '%s/%s/locale' % (PluginGroup,PluginFolder))

try:
    from Components.LanguageGOS import gosgettext as _
except:
    from Components.Language import language
    import gettext
    from os import environ

    def localeInit():
        lang = language.getLanguage()[:2]
        environ["LANGUAGE"] = lang
        gettext.bindtextdomain(PluginLanguageDomain, PluginLanguagePath)

    def _(txt):
        t = gettext.dgettext(PluginLanguageDomain, txt)
        if t == txt:
                t = gettext.gettext(txt)
        return t

    localeInit()
    language.addCallback(localeInit)


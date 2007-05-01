from zope.component import queryUtility
from zope.interface import implements

from Acquisition import aq_inner, aq_base
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFPlone.interfaces import IBrowserDefault
from Products.CMFPlone.interfaces import IDynamicViewTypeInformation
from Products.CMFPlone import utils
from Products.Five.browser import BrowserView

from plone.app.layout.navigation.interfaces import IDefaultPage

class DefaultPage(BrowserView):
    implements(IDefaultPage)

    def isDefaultPage(self, obj, context_=None):
        """Finds out if the given obj is the default page in its parent folder.

        Only considers explicitly contained objects, either set as index_html,
        with the default_page property, or using IBrowserDefault.
        """
        #XXX: What is this context/obj confusion all about?
        if context_ is None:
            context_ = obj
        parentDefaultPage = self.getDefaultPage(context_)
        if parentDefaultPage is None or '/' in parentDefaultPage:
            return False
        return (parentDefaultPage == obj.getId())

    def getDefaultPage(self, context_=None):
        """Given a folderish item, find out if it has a default-page using
        the following lookup rules:

            1. A content object called 'index_html' wins
            2. If the folder implements IBrowserDefault, query this
            3. Else, look up the property default_page on the object
                - Note that in this case, the returned id may *not* be of an
                  object in the folder, since it could be acquired from a
                  parent folder or skin layer
            4. Else, look up the property default_page in site_properties for
                magic ids and test these

        The id of the first matching item is then used to lookup a translation
        and if found, its id is returned. If no default page is set, None is
        returned. If a non-folderish item is passed in, return None always.
        """
        context = aq_inner(self.context)
        if context_ is None:
            context_ = context

        # The list of ids where we look for default
        ids = {}

        # For BTreeFolders we just use the has_key, otherwise build a dict
        if hasattr(aq_base(context), 'has_key'):
            ids = context
        else:
            for id in context.objectIds():
                ids[id] = 1

        # Inline function with default argument.
        def lookupTranslationId(obj, page):
            return utils.lookupTranslationId(obj, page, ids)

        # 1. test for contentish index_html
        if ids.has_key('index_html'):
            return lookupTranslationId(context, 'index_html')

        # 2. Test for IBrowserDefault
        browserDefault = IBrowserDefault(context, None)
        if browserDefault is not None:
            fti = context.getTypeInfo()
            if fti is not None:
                dynamicFTI = IDynamicViewTypeInformation(fti, None)
                if dynamicFTI is not None:
                    page = dynamicFTI.getDefaultPage(context, check_exists=True)
                    if page is not None:
                        return lookupTranslationId(context, page)

        # 3. Test for default_page property in folder, then skins
        pages = getattr(aq_base(context), 'default_page', [])
        if isinstance(pages, basestring):
            pages = [pages]
        for page in pages:
            if page and ids.has_key(page):
                return lookupTranslationId(context, page)

        portal = queryUtility(ISiteRoot)
        # Might happen during portal creation
        if portal is not None:
            for page in pages:
                if portal.unrestrictedTraverse(page, None):
                    return lookupTranslationId(context, page)

            # 4. Test for default sitewide default_page setting
            site_properties = portal.portal_properties.site_properties
            for page in site_properties.getProperty('default_page', []):
                if ids.has_key(page):
                    return lookupTranslationId(context, page)

        return None
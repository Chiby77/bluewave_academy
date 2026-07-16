"""
Cache-invalidation signals for Bluewave Academy.

When a BlogPost or Announcement is saved/deleted, the corresponding
template fragment cache keys are immediately invalidated so the next
request gets fresh data without waiting for the TTL to expire.
"""
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


# Keys must match those used in the templates
HOME_BLOG_CARDS_KEY = "home_blog_cards"
HOME_ANNOUNCEMENTS_KEY = "home_announcements"
BLOG_GRID_KEY = "blog_grid"
DOWNLOADS_LIST_KEY = "downloads_list"


def _invalidate_home_blog(sender, **kwargs):
    cache.delete(HOME_BLOG_CARDS_KEY)
    cache.delete(BLOG_GRID_KEY)


def _invalidate_home_announcements(sender, **kwargs):
    cache.delete(HOME_ANNOUNCEMENTS_KEY)


def _invalidate_downloads(sender, **kwargs):
    cache.delete(DOWNLOADS_LIST_KEY)


# Lazy imports to avoid circular import at module load time.
# Signals are connected inside SiteappConfig.ready() in apps.py.
def connect_signals():
    from .models import BlogPost, Announcement, DownloadResource

    post_save.connect(_invalidate_home_blog, sender=BlogPost)
    post_delete.connect(_invalidate_home_blog, sender=BlogPost)

    post_save.connect(_invalidate_home_announcements, sender=Announcement)
    post_delete.connect(_invalidate_home_announcements, sender=Announcement)

    post_save.connect(_invalidate_downloads, sender=DownloadResource)
    post_delete.connect(_invalidate_downloads, sender=DownloadResource)

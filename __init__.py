def classFactory(iface):
    from .brick_annotator import BrickAnnotatorPlugin
    return BrickAnnotatorPlugin(iface)
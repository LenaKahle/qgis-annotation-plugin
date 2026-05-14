def classFactory(iface):
    from .src.annotator import BrickAnnotatorPlugin
    return BrickAnnotatorPlugin(iface)
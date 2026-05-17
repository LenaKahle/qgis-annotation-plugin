def classFactory(iface):
    from .src.annotator import AnnotatorPlugin
    return AnnotatorPlugin(iface)
"""Seznam podporovaných realitních portálů."""
from .bezrealitky import Bezrealitky
from .eurobydleni import EuroBydleni
from .idnes import Idnes
from .mmreality import MMReality
from .realcity import Realcity
from .realingo import Realingo
from .realitycz import RealityCz
from .remax import Remax
from .sreality import Sreality
from .ulovdomov import UlovDomov

ALL = [Sreality, Idnes, Bezrealitky, Realingo, UlovDomov, Remax, Realcity, EuroBydleni, RealityCz, MMReality]

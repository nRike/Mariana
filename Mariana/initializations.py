import Mariana.settings as MSET
import Mariana.useful as MUSE
from Mariana.abstraction import Abstraction_ABC

import lasagne.init as LI

import numpy
import theano
import theano.tensor as tt

__all__= [
    "Initialization_ABC",
    "Identity",
    "HardSet",
    "SingleValue",
    "Normal",
    "Uniform",
    "FanInFanOut_ABC",
    "GlorotNormal",
    "GlorotUniform",
    "HeNormal",
    "HeUniform",
]

class Initialization_ABC(Abstraction_ABC) :
    """This class defines the interface that an Initialization must offer.
    
    :param string parameter: the name of the parameter to be initialized
    :param float parameter: how sparse should the result be. 0 => no sparsity, 1 => a matrix of zeros
    """

    def __init__(self, parameter, sparsity=0., *args, **kwargs):
        super(ClassName, self).__init__(*args, **kwargs)
        self.setHP("parameter", parameter)
        
    def apply(self, layer) :
        message = "%s was initialized using %s" % (layer.name, self.__class__.__name__)
        try :
            if (v.shape != layer.getParameterShape(self.getHP("parameter"))) :
                raise ValueError("Initialization has a wrong shape: %s, parameter shape is: %s " % (v.shape, layer.getParameterShape(self.getHP("parameter"))))
            v = MUSE.iCast_numpy(self.run(layer.getParameterShape(self.getHP("parameter"))))
            v = MUSE.sparsify(v, sparsity)
            layer.initParameter( self.getHP("parameter"), theano.shared(value = v, name = "%s_%s" % (layer.name, self.parameter) ) )
        except Exception as e:
            message = "%s was *NOT* initialized using %s. Because: %s" % (layer.name, self.__class__.__name__, e.message)
            layer.network.logLayerEvent(layer, message, self.getHyperParameters())
            raise e
        
    def run(self, shape) :
        """The function that all Initialization_ABCs must implement"""
        raise NotImplemented("This one should be implemented in child")

class Identity(Initialization_ABC) :
    """Identity matrix. Its your job to make sure that the parameter is a square matrix"""
    def run(self, shape) :
        v = numpy.identity(shape, dtype = theano.config.floatX)

class HardSet(Initialization_ABC) :
    """Sets the parameter to value. It's your job to make sure that the shape is correct"""
    def __init__(self, parameter, value, *args, **kwargs) :
        Initialization_ABC.__init__(self, *args, **kwargs)
        self.parameter = parameter
        self.value = numpy.asarray(value, dtype=theano.config.floatX)
        self.hyperParameters = ["parameter"]

    def run(self, shape) :

class SingleValue(Initialization_ABC) :
    """Initialize to a given value"""
    def __init__(self, parameter, value, *args, **kwargs) :
        super(SingleValue, self).__init__(parameter, *args, **kwargs)
        self.setHP("value", value)
    
    def run(self, shape) :
        return numpy.ones(shape) * self.getHP("value")
        return self.value

class Normal(Initialization_ABC):
    """
    Initializes using a random normal distribution.
    **Small** uses my personal initialization than I find works very well in most cases with a uniform distribution, simply divides by the sum of the weights.
    """
    def __init__(self, std, mean, small=False):
        super(Normal, self).__init__()
        self.setHP("std", std)
        self.setHP("mean", mean)
        self.setHP("small", small)
    
    def run(self, shape) :
        v = numpy.random.normal(self.getHP("mean"), self.getHP("std"), size=shape)
        if self.getHP("small") :
            return v / numpy.sum(v)
        return v

class Uniform(Initialization_ABC):
    """
    Initializes using a uniform distribution
    **Small** uses my personal initialization than I works very well in most cases, simply divides by the sum of the weights.
    """
    def __init__(self, low, high, small=False):
        super(Uniform, self).__init__()
        self.setHP("low", low)
        self.setHP("high", high)
    
    def run(self, shape) :
        v = numpy.random.uniform(high=self.getHP("high"), low=self.getHP("low"), size=shape)
        if self.getHP("small") :
            return v / numpy.sum(v)
        return v

class FanInFanOut_ABC(Initialization_ABC) :
    """
    Abtract class for fan_in/_out inits (Glorot and He)
    Over the time people have introduced
    ways to make it work with other various activation functions by modifying a gain factor.
    You can force the gain using the *forceGain* argument, otherwise Mariana will choose
    one for you depending on the layer's activation.

        * ReLU: sqrt(2)
        
        * LeakyReLU: sqrt(2/(1+alpha**2)) where alpha is the leakiness

        * Everything else : 1.0
    
    This is an abtract class: see *GlorotNormal*, *GlorotUniform*
    """
    def __init__(self, parameter, forceGain=None, *args, **kwargs) :
        super(FanInFanOut_ABC, self).__init__(parameter, *args, **kwargs)
        self.setHP("forceGain", forceGain)
        self.gain = None

    def _getGain(activation) :
    """returns the gain with respesct to an activation function"""

    if activation.__class__ is MA.ReLU :
        if activation.leakiness == 0 :
            return numpy.sqrt(2)
        else :
            return numpy.sqrt(2/(1+activation.leakiness**2))
    return 1.0

    def apply(self, layer) :
        import Mariana.activations as MA

        forceGain = self.getHP("forceGain")
        if forceGain :
            self.gain = forceGain
        else :
            self.gain = self._getGain(layer.abstractions["activation"])
        
        return super(FanInFanOut_ABC, self).apply(layer)

class GlorotNormal(FanInFanOut_ABC) :
    """
    Initialization strategy introduced by Glorot et al. 2010 on a Normal distribution.
    If you use tanh() as activation try this one first.
    Uses lasagne as backend.
    """ 
    def run(self, shape) :
        return LI.GlorotNormal(gain = self.gain).sample()

class GlorotUniform(FanInFanOut_ABC) :
    """
    Initialization strategy introduced by Glorot et al. 2010 on a Uniform distribution.
    Uses lasagne as backend.
    """ 
    def run(self, shape) :
        return LI.GlorotUniform(gain = self.gain).sample()

class HeNormal(FanInFanOut_ABC) :
    """
    Initialization proposed by He et al. for ReLU in *Delving Deep into Rectifiers: Surpassing Human-Level Performance on ImageNet Classification*, 2015.
    
    On a Normal distribution, Uses lasagne as backend.
    """ 
    def run(self, shape) :
        return LI.HeNormal(gain = self.gain).sample()

class HeUniform(FanInFanOut_ABC) :
    """
    Initialization proposed by He et al. for ReLU in *Delving Deep into Rectifiers: Surpassing Human-Level Performance on ImageNet Classification*, 2015.
    
    On a Uniform distribution, Uses lasagne as backend.
    """ 
    def run(self, shape) :
        return LI.HeUniform(gain = self.gain).sample()
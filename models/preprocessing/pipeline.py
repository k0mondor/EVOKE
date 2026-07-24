from dataclasses import dataclass, field

from .artifact import ICAConfig, run_ica
from .filters import FilterConfig, apply_bandpass, apply_notch, apply_rereference
from .windowing import WindowConfig, build_windows


@dataclass(slots=True)
class PreprocessingPipeline:
    filter_config: FilterConfig = field(default_factory=FilterConfig)
    ica_config: ICAConfig = field(default_factory=ICAConfig)
    window_config: WindowConfig = field(default_factory=WindowConfig)

    def clean(self, signal):
        signal = apply_rereference(signal, self.filter_config)
        signal = apply_bandpass(signal, self.filter_config)
        signal = apply_notch(signal, self.filter_config)
        return run_ica(signal, self.ica_config)

    def transform(self, signal):
        return build_windows(self.clean(signal), self.window_config)

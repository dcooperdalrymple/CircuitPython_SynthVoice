# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: MIT

import ulab.numpy as np
import synthio
import synthvoice
import synthwaveform

class Voice(synthvoice.Voice):
    """Base single-shot "analog" drum voice used by other classes within the percussive module.
    Handles envelope times, tuning, waveforms, etc. for multiple :class:`synthio.Note` objects.

    :param count: The number of :class:`synthio.Note` objects to generate. Defaults to 3.
    :param filter_type: The type of filter to use as designated by the constants within
        :class:`synthvoice.FilterType` enum. Defaults to :const:`synthvoice.FilterType.LOWPASS`.
    :param filter_frequency: The exact frequency of the filter of all :class:`synthio.Note` objects
        in hertz. Defaults to 20000hz.
    :param frequencies: A list of the frequencies corresponding to each :class:`synthio.Note` object
        in hertz. Voice doesn't respond to the note frequency when pressed and instead uses these
        constant frequencies. Defaults to 440.0hz if not provided.
    :param times: A list of decay times corresponding to each :class:`synthio.Note` objects'
        amplitude envelope in seconds. Defaults to 1.0s for all notes if not provided.
    :param waveforms: A list of waveforms corresponding to each :class:`synthio.Note` object as
        :class:`numpy.int16` arrays. Defaults to a square waveform for each note.
    """

    def __init__(self, synthesizer:synthio.Synthesizer=None, count:int=3, filter_type:int=synthvoice.FilterType.LOWPASS, filter_frequency:float=20000.0, frequencies:tuple[float]=[], times:tuple[float]=[], waveforms:tuple[np.ndarray]=[]):
        super().__init__(synthesizer)

        if not frequencies:
            frequencies = tuple([440.0])
        if not times:
            times = tuple([1.0])

        self._times = times
        self._attack_level = 1.0

        self._lfo = synthio.LFO(
            waveform=np.array([32767, -32768], dtype=np.int16),
            rate=20.0,
            scale=0.3,
            offset=0.33,
            once=True
        )

        self._notes = []
        for i in range(count):
            self._notes.append(synthio.Note(
                frequency=frequencies[i % len(frequencies)],
                bend=self._lfo
            ))
        self._notes = tuple(self._notes)

        self.times = times
        self.waveforms = waveforms

        self.filter_type = filter_type
        self.filter_frequency = filter_frequency

    @property
    def notes(self) -> tuple[synthio.Note]:
        return self._notes
    
    @property
    def blocks(self) -> tuple[synthio.BlockInput]:
        return tuple([self._lfo])
    
    @property
    def frequencies(self) -> tuple[float]:
        """The base frequencies in hertz."""
        value = []
        for note in self.notes:
            value.append(note.frequency)
        return tuple(value)

    @frequencies.setter
    def frequencies(self, value:tuple[float]|float) -> None:
        if not isinstance(value, tuple):
            value = tuple([value])
        if value:
            for i, note in enumerate(self.notes):
                note.frequency = value[i % len(value)]

    @property
    def times(self) -> tuple[float]:
        """The decay times of the amplitude envelopes."""
        return self._times
    
    @times.setter
    def times(self, value:tuple[float]|float) -> None:
        if not isinstance(value, tuple): value = tuple([value])
        if value:
            self._times = value
            self._update_envelope()

    @property
    def waveforms(self) -> tuple[np.ndarray]:
        """The note waveforms as :class:`ulab.numpy.ndarray` objects with the
        :class:`ulab.numpy.int16` data type.
        """
        value = []
        for note in self.notes:
            value.append(note.waveform)
        return tuple(value)
    
    @waveforms.setter
    def waveforms(self, value:tuple[np.ndarray]) -> None:
        if not value: return
        for i, note in enumerate(self.notes):
            note.waveform = value[i % len(value)]

    def press(self, velocity:float|int=1.0) -> bool:
        """Update the voice to be "pressed". For percussive voices, this will begin the playback of
        the voice.

        :param velocity: The strength at which the note was received, between 0.0 and 1.0.
        """
        if not super().press(1, velocity):
            return False
        self._lfo.retrigger()
        return True
    
    def release(self) -> bool:
        """Release the voice. :class:`synthvoice.percussive.Voice` objects typically don't implement
        this operation because of their "single-shot" nature and will always return `False`.
        """
        super().release()
        return False
    
    @property
    def amplitude(self) -> float:
        """The volume of the voice from 0.0 to 1.0."""
        return self.notes[0].amplitude
    
    @amplitude.setter
    def amplitude(self, value:float) -> None:
        for note in self.notes:
            note.amplitude = min(max(value, 0.0), 1.0)

    def _update_envelope(self) -> None:
        mod = self._get_velocity_mod()
        for i, note in enumerate(self.notes):
            note.envelope = synthio.Envelope(
                attack_time=0.0,
                decay_time=self._times[i % len(self._times)],
                release_time=0.0,
                attack_level=mod*self._attack_level,
                sustain_level=0.0
            )

    @property
    def attack_level(self) -> float:
        """The level of attack of the amplitude envelope."""
        return self._attack_level
    
    @attack_level.setter
    def attack_level(self, value:float) -> None:
        self._attack_level = value
        self._update_envelope()

class Kick(Voice):
    """A single-shot "analog" drum voice representing a low frequency sine-wave kick drum."""

    def __init__(self, synthesizer:synthio.Synthesizer=None):
        sine=synthwaveform.sine()
        offset_sine=synthwaveform.sine(phase=0.5)
        super().__init__(
            synthesizer,
            count=3,
            filter_frequency=2000.0,
            frequencies=(53.0, 72.0, 41.0),
            times=(0.075, 0.055, 0.095),
            waveforms=(offset_sine, sine, offset_sine),
        )

class Snare(Voice):
    """A single-shot "analog" drum voice representing a snare drum using sine and noise waveforms.
    """

    def __init__(self, synthesizer:synthio.Synthesizer=None):
        sine_noise=synthwaveform.mix(
            synthwaveform.sine(),
            (synthwaveform.noise(), 0.5),
        )
        offset_sine_noise=synthwaveform.mix(
            synthwaveform.sine(phase=0.5),
            (synthwaveform.noise(), 0.5),
        )
        super().__init__(
            synthesizer,
            count=3,
            filter_frequency=9500.0,
            frequencies=(90.0, 135.0, 165.0),
            times=(0.115, 0.095, 0.115),
            waveforms=(sine_noise, offset_sine_noise, offset_sine_noise),
        )

class Hat(Voice):
    """The base class to create hi-hat drum sounds with variable timing.

    :param min_time: The minimum decay time in seconds. Must be greater than 0.0s.
    :param max_time: The maximum decay time in seconds. Must be greater than `min_time`.
    """

    def __init__(self, min_time:float, max_time:float, synthesizer:synthio.Synthesizer=None):
        super().__init__(
            synthesizer,
            count=3,
            filter_type=synthvoice.FilterType.HIGHPASS,
            filter_frequency=9500.0,
            frequencies=(90, 135, 165.0),
            waveforms=[synthwaveform.noise()]
        )
        self._min_time = max(min_time, 0.0)
        self._max_time = max(max_time, self._min_time)
        self.decay = 0.5

    @property
    def decay(self) -> float:
        """The decay time of the hi-hat using a relative value from 0.0 to 1.0 and the predefined
        minimum and maximum times.
        """
        return self._decay
    
    @decay.setter
    def decay(self, value:float) -> None:
        value = min(max(value, 0.0), 1.0) * (self._max_time - self._min_time) + self._min_time
        self.times = (value, max(value - 0.02, 0.0), value)

class ClosedHat(Hat):
    """A single-shot "analog" drum voice representing a closed hi-hat cymbal using noise waveforms.
    """

    def __init__(self, synthesizer:synthio.Synthesizer=None):
        super().__init__(0.025, 0.2, synthesizer)

class OpenHat(Hat):
    """A single-shot "analog" drum voice representing an open hi-hat cymbal using noise waveforms.
    """

    def __init__(self, synthesizer:synthio.Synthesizer=None):
        super().__init__(0.25, 1.0, synthesizer)

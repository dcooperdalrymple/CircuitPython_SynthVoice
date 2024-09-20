# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: MIT

import synthio
import synthwaveform
import ulab.numpy as np

import synthvoice

try:
    from circuitpython_typing import ReadableBuffer
except ImportError:
    pass


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

    def __init__(  # noqa: PLR0913
        self,
        synthesizer: synthio.Synthesizer,
        count: int = 3,
        filter_type: int = synthvoice.FilterType.LOWPASS,
        filter_frequency: float = 20000.0,
        frequencies: tuple[float] = [],
        times: tuple[float] = [],
        waveforms: tuple[ReadableBuffer] | ReadableBuffer = [],
    ):
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
            once=True,
        )

        self._notes = []
        for i in range(count):
            self._notes.append(
                synthio.Note(frequency=frequencies[i % len(frequencies)], bend=self._lfo)
            )
        self._notes = tuple(self._notes)

        self.times = times
        self.waveforms = waveforms

        self.filter_type = filter_type
        self.filter_frequency = filter_frequency

    @property
    def notes(self) -> tuple[synthio.Note]:
        """Get all :class:`synthio.Note` objects attributed to this voice."""
        return self._notes

    @property
    def blocks(self) -> tuple[synthio.BlockInput]:
        """Get all :class:`synthio.BlockInput` objects attributed to this voice."""
        return tuple([self._lfo])

    @property
    def frequencies(self) -> tuple[float]:
        """The base frequencies in hertz."""
        value = []
        for note in self.notes:
            value.append(note.frequency)
        return tuple(value)

    @frequencies.setter
    def frequencies(self, value: tuple[float] | float) -> None:
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
    def times(self, value: tuple[float] | float) -> None:
        if not isinstance(value, tuple):
            value = tuple([value])
        if value:
            self._times = value
            self._update_envelope()

    @property
    def waveforms(self) -> tuple[ReadableBuffer]:
        """The note waveforms as :class:`ulab.numpy.ndarray` objects with the
        :class:`ulab.numpy.int16` data type.
        """
        value = []
        for note in self.notes:
            value.append(note.waveform)
        return tuple(value)

    @waveforms.setter
    def waveforms(self, value: tuple[ReadableBuffer] | ReadableBuffer) -> None:
        if not value:
            return
        if not isinstance(value, tuple):
            value = tuple([value])
        for i, note in enumerate(self.notes):
            note.waveform = value[i % len(value)]

    def press(self, velocity: float | int = 1.0) -> bool:
        """Update the voice to be "pressed". For percussive voices, this will begin the playback of
        the voice.

        :param velocity: The strength at which the note was received, between 0.0 and 1.0.
        """
        super().release()
        super().press(1, velocity)
        self._lfo.retrigger()
        return True

    def release(self) -> bool:
        """Release the voice. :class:`synthvoice.percussive.Voice` objects typically don't implement
        this operation because of their "single-shot" nature and will always return `False`.
        """
        return False

    @property
    def amplitude(self) -> float:
        """The volume of the voice from 0.0 to 1.0."""
        return self.notes[0].amplitude

    @amplitude.setter
    def amplitude(self, value: float) -> None:
        for note in self.notes:
            note.amplitude = min(max(value, 0.0), 1.0)

    def _update_envelope(self) -> None:
        mod = self._get_velocity_mod()
        for i, note in enumerate(self.notes):
            note.envelope = synthio.Envelope(
                attack_time=0.0,
                decay_time=self._times[i % len(self._times)],
                release_time=0.0,
                attack_level=mod * self._attack_level,
                sustain_level=0.0,
            )

    @property
    def attack_level(self) -> float:
        """The level of attack of the amplitude envelope."""
        return self._attack_level

    @attack_level.setter
    def attack_level(self, value: float) -> None:
        self._attack_level = value
        self._update_envelope()


class Kick(Voice):
    """A single-shot "analog" drum voice representing a low frequency sine-wave kick drum."""

    def __init__(self, synthesizer: synthio.Synthesizer):
        sine = synthwaveform.sine()
        offset_sine = synthwaveform.sine(phase=0.5)
        super().__init__(
            synthesizer,
            count=3,
            filter_frequency=2000.0,
            frequencies=(53.0, 72.0, 41.0),
            times=(0.075, 0.055, 0.095),
            waveforms=(offset_sine, sine, offset_sine),
        )


class Snare(Voice):
    """A single-shot "analog" drum voice representing a snare drum using sine and noise
    waveforms.
    """

    def __init__(self, synthesizer: synthio.Synthesizer):
        sine_noise = synthwaveform.mix(
            synthwaveform.sine(),
            (synthwaveform.noise(), 0.5),
        )
        offset_sine_noise = synthwaveform.mix(
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


class Cymbal(Voice):
    """The base class to create cymbal sounds with variable timing.

    :param min_time: The minimum decay time in seconds. Must be greater than 0.0s.
    :param max_time: The maximum decay time in seconds. Must be greater than min_time.
    """

    def __init__(
        self,
        synthesizer: synthio.Synthesizer,
        min_time: float,
        max_time: float,
        frequency: float = 9500.0,
    ):
        super().__init__(
            synthesizer,
            count=3,
            filter_type=synthvoice.FilterType.HIGHPASS,
            filter_frequency=frequency,
            frequencies=(90, 135, 165.0),
            waveforms=synthwaveform.noise(),
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
    def decay(self, value: float) -> None:
        self._decay = min(max(value, 0.0), 1.0)
        value = self._decay * (self._max_time - self._min_time) + self._min_time
        self.times = (value, max(value - 0.02, 0.0), value)


class ClosedHat(Cymbal):
    """A single-shot "analog" drum voice representing a closed hi-hat cymbal using noise
    waveforms.
    """

    def __init__(self, synthesizer: synthio.Synthesizer):
        super().__init__(synthesizer, 0.025, 0.2)


class OpenHat(Cymbal):
    """A single-shot "analog" drum voice representing an open hi-hat cymbal using noise
    waveforms.
    """

    def __init__(self, synthesizer: synthio.Synthesizer):
        super().__init__(synthesizer, 0.25, 1.0)


class Ride(Cymbal):
    """A single-shot "analog" drum voice representing a ride cymbal using noise waveforms."""

    def __init__(self, synthesizer: synthio.Synthesizer):
        super().__init__(synthesizer, 0.5, 2.0, 18000.0)


class Tom(Voice):
    """The base class to create tom drum sounds with variable timing and frequency.

    :param min_time: The minimum decay time in seconds. Must be greater than 0.0s.
    :param max_time: The maximum decay time in seconds. Must be greater than min_time.
    :param min_frequency: The minimum frequency in hertz.
    :param max_frequency: The maximum frequency in hertz.
    """

    def __init__(  # noqa: PLR0913
        self,
        synthesizer: synthio.Synthesizer,
        min_time: float,
        max_time: float,
        min_frequency: float,
        max_frequency: float,
    ):
        super().__init__(
            synthesizer,
            count=2,
            filter_frequency=4000.0,
            waveforms=(synthwaveform.triangle(), synthwaveform.noise(amplitude=0.25)),
        )
        self._min_time = max(min_time, 0.0)
        self._max_time = max(max_time, self._min_time)
        self.decay = 0.5

        self._min_frequency = max(min_frequency, 0.0)
        self._max_frequency = max(max_frequency, self._min_frequency)
        self.frequency = 0.5

    @property
    def decay(self) -> float:
        """The decay time of the tom drum using a relative value from 0.0 to 1.0 and the predefined
        minimum and maximum times.
        """
        return self._decay

    @decay.setter
    def decay(self, value: float) -> None:
        self._decay = min(max(value, 0.0), 1.0)
        self.times = (self._decay * (self._max_time - self._min_time) + self._min_time, 0.025)

    @property
    def frequency(self) -> float:
        """The note frequency of the tom drum using a relative value from 0.0 to 1.0 and the
        predefined minimum and maximum frequencies.
        """
        return self._frequency

    @frequency.setter
    def frequency(self, value: float) -> None:
        self._frequency = min(max(value, 0.0), 1.0)
        self.frequencies = (
            self._frequency * (self._max_frequency - self._min_frequency) + self._min_frequency
        )


class HighTom(Tom):
    """A single-shot "analog" drum voice representing a high or left rack tom drum."""

    def __init__(self, synthesizer: synthio.Synthesizer):
        super().__init__(synthesizer, 0.1, 0.45, 261.63, 293.66)


class MidTom(Tom):
    """A single-shot "analog" drum voice representing a middle or right rack tom drum."""

    def __init__(self, synthesizer: synthio.Synthesizer):
        super().__init__(synthesizer, 0.1, 0.45, 185.00, 207.65)


class FloorTom(Tom):
    """A single-shot "analog" drum voice representing a low or floor tom drum."""

    def __init__(self, synthesizer: synthio.Synthesizer):
        super().__init__(synthesizer, 0.1, 0.65, 116.54, 146.83)

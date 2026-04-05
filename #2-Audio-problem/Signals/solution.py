import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import butter, filtfilt, iirnotch, hilbert, find_peaks



def normalize(x):
    max_val = np.max(np.abs(x))
    if max_val == 0:
        return x
    return x / max_val


def plot_time(signal, fs, title, filename):
    t = np.arange(len(signal)) / fs
    plt.figure(figsize=(10, 4))
    plt.plot(t[:2000], signal[:2000])
    plt.title(title)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.grid()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


def plot_fft(signal, fs, title, filename):
    N = len(signal)
    X = np.fft.rfft(signal)
    f = np.fft.rfftfreq(N, 1 / fs)

    plt.figure(figsize=(10, 4))
    plt.plot(f, np.abs(X))
    plt.title(title)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.xlim(0, 10000)
    plt.grid()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

    return f, np.abs(X)


def plot_phase(signal, fs, title, filename):
    N = len(signal)
    X = np.fft.rfft(signal)
    f = np.fft.rfftfreq(N, 1 / fs)
    phase = np.unwrap(np.angle(X))

    plt.figure(figsize=(10, 4))
    plt.plot(f, phase)
    plt.title(title)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Phase (radians)")
    plt.xlim(0, 4000)
    plt.grid()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


def lowpass(x, cutoff, fs):
    b, a = butter(5, cutoff / (fs / 2), btype="low")
    return filtfilt(b, a, x)


def notch(x, f0, fs, Q=30):
    b, a = iirnotch(f0 / (fs / 2), Q)
    return filtfilt(b, a, x)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, "corrupted.wav")
    plots_dir = os.path.join(base_dir, "plots")
    output_file = os.path.join(base_dir, "recovered.wav")

    os.makedirs(plots_dir, exist_ok=True)

    fs, data = wavfile.read(input_file)

  
    if len(data.shape) == 2:
        data = data[:, 0]

    signal = data.astype(np.float64)
    signal = normalize(signal)

    plot_time(
        signal,
        fs,
        "Stage 1: Corrupted Signal in Time Domain",
        os.path.join(plots_dir, "stage1_time_domain.png"),
    )
    f, mag = plot_fft(
        signal,
        fs,
        "Stage 1: FFT of Corrupted Signal",
        os.path.join(plots_dir, "stage1_fft.png"),
    )

  
    fc = f[np.argmax(mag)]
    print("Estimated carrier frequency:", fc)

    t = np.arange(len(signal)) / fs
    mixed = signal * np.cos(2 * np.pi * fc * t)

    plot_time(
        mixed,
        fs,
        "Stage 2: Mixed Signal in Time Domain",
        os.path.join(plots_dir, "stage2_mixed_time.png"),
    )
    plot_fft(
        mixed,
        fs,
        "Stage 2: FFT After Mixing",
        os.path.join(plots_dir, "stage2_mixed_fft.png"),
    )

    demod = lowpass(mixed, 4000, fs)
    demod = normalize(demod)

    plot_time(
        demod,
        fs,
        "Stage 2: Demodulated Signal in Time Domain",
        os.path.join(plots_dir, "stage2_recovered_time.png"),
    )
    f2, mag2 = plot_fft(
        demod,
        fs,
        "Stage 2: FFT After Frequency Shift Correction",
        os.path.join(plots_dir, "stage2_recovered_fft.png"),
    )


    plot_fft(
        demod,
        fs,
        "Stage 3: FFT Before Notch Filtering",
        os.path.join(plots_dir, "stage3_fft_before.png"),
    )

    peaks, _ = find_peaks(mag2, height=np.max(mag2) / 5)
    spike_freqs = f2[peaks]
    print("Detected spikes:", spike_freqs)

    clean = demod.copy()
    for sf in spike_freqs:
        if 80 < sf < 3900:
            clean = notch(clean, sf, fs)

    clean = normalize(clean)

    plot_time(
        clean,
        fs,
        "Stage 3: Signal After Notch Filtering",
        os.path.join(plots_dir, "stage3_time_after.png"),
    )
    plot_fft(
        clean,
        fs,
        "Stage 3: FFT After Notch Filtering",
        os.path.join(plots_dir, "stage3_fft_after.png"),
    )


    plot_phase(
        clean,
        fs,
        "Stage 4: Phase Before Final Correction",
        os.path.join(plots_dir, "stage4_phase_before.png"),
    )

    final1 = clean
    final2 = -clean
    final3 = clean[::-1]

    analytic = hilbert(clean)
    final4 = -np.imag(analytic)

    wavfile.write(
        os.path.join(base_dir, "candidate_clean.wav"),
        fs,
        (normalize(final1) * 32767).astype(np.int16),
    )
    wavfile.write(
        os.path.join(base_dir, "candidate_negated.wav"),
        fs,
        (normalize(final2) * 32767).astype(np.int16),
    )
    wavfile.write(
        os.path.join(base_dir, "candidate_reversed.wav"),
        fs,
        (normalize(final3) * 32767).astype(np.int16),
    )
    wavfile.write(
        os.path.join(base_dir, "candidate_hilbert.wav"),
        fs,
        (normalize(final4) * 32767).astype(np.int16),
    )

  
    final = final4
    final = normalize(final)

    plot_phase(
        final,
        fs,
        "Stage 4: Phase After Final Correction",
        os.path.join(plots_dir, "stage4_phase_after.png"),
    )
    plot_time(
        final,
        fs,
        "Stage 4: Final Signal",
        os.path.join(plots_dir, "stage4_final.png"),
    )

    wavfile.write(output_file, fs, (final * 32767).astype(np.int16))

    print("Saved 4 candidate outputs. Listen and choose best.")
    print("Done! recovered.wav generated.")



if __name__ == "__main__":
    main()
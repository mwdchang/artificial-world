import argparse
import json

import matplotlib

matplotlib.use("Agg")

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import SymLogNorm


def load_simulation(path):
    with open(path) as f:
        data = json.load(f)

    if "states" in data:
        states = data["states"]
    else:
        states = data

    names = list(states.keys())
    if not names:
        raise ValueError("No states found in the simulation file.")

    arrays = {name: np.asarray(states[name], dtype=float) for name in names}

    shapes = {name: arr.shape for name, arr in arrays.items()}
    if len(set(shapes.values())) != 1:
        raise ValueError(f"States have mismatched shapes: {shapes}")

    frames = next(iter(shapes.values()))[0]
    times = data.get("times")
    if times is None or len(times) != frames:
        times = list(range(frames))
    times = np.asarray(times, dtype=float)

    return names, arrays, times


def make_gif(
    path,
    output,
    fps=10,
    cmap="viridis",
    per_state=False,
    dpi=100,
    loop=0,
    log_scale=False,
    linthresh=1.0,
):
    names, arrays, times = load_simulation(path)
    frames = len(times)

    if per_state:
        clims = {
            name: (arr.min(), arr.max()) for name, arr in arrays.items()
        }
    else:
        vmin = min(arr.min() for arr in arrays.values())
        vmax = max(arr.max() for arr in arrays.values())
        clims = {name: (vmin, vmax) for name in names}

    n = len(names)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4.5), squeeze=False)
    axes = axes[0]

    images = []
    for ax, name in zip(axes, names):
        lo, hi = clims[name]
        if log_scale:
            # SymLogNorm keeps zeros (and negatives) valid: values within
            # +/-linthresh are shown on a linear scale, beyond it on a log
            # scale. Guard against a flat range so the norm stays valid.
            if hi <= lo:
                hi = lo + max(linthresh, 1.0)
            norm = SymLogNorm(linthresh=linthresh, vmin=lo, vmax=hi)
            img = ax.imshow(
                arrays[name][0],
                cmap=cmap,
                norm=norm,
                interpolation="nearest",
            )
        else:
            img = ax.imshow(
                arrays[name][0],
                cmap=cmap,
                vmin=lo,
                vmax=hi,
                interpolation="nearest",
            )
        ax.set_title(name)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(img, ax=ax, fraction=0.046, pad=0.04)
        images.append(img)

    suptitle = fig.suptitle("")

    def update(frame):
        for img, name in zip(images, names):
            img.set_data(arrays[name][frame])
        suptitle.set_text(f"t = {times[frame]:.4g}")
        return images + [suptitle]

    anim = animation.FuncAnimation(
        fig,
        update,
        frames=frames,
        interval=1000 / fps,
        blit=False,
    )

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    anim.save(output, writer=animation.PillowWriter(fps=fps), dpi=dpi)
    plt.close(fig)
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Convert a grid ODE simulation JSON into an animated GIF."
    )
    parser.add_argument("input", help="Path to the simulation JSON file.")
    parser.add_argument(
        "-o",
        "--output",
        default="simulation.gif",
        help="Output GIF path (default: simulation.gif).",
    )
    parser.add_argument(
        "--fps", type=float, default=10, help="Frames per second (default: 10)."
    )
    parser.add_argument(
        "--cmap", default="viridis", help="Matplotlib colormap (default: viridis)."
    )
    parser.add_argument(
        "--per-state",
        action="store_true",
        help="Normalize the color scale independently for each state.",
    )
    parser.add_argument(
        "--dpi", type=int, default=100, help="Output resolution (default: 100)."
    )
    parser.add_argument(
        "--log-scale",
        action="store_true",
        help="Use a symlog color scale (handles zeros and negatives).",
    )
    parser.add_argument(
        "--linthresh",
        type=float,
        default=1.0,
        help="Symlog linear region +/- this value around zero (default: 1.0).",
    )
    args = parser.parse_args()

    output = make_gif(
        args.input,
        args.output,
        fps=args.fps,
        cmap=args.cmap,
        per_state=args.per_state,
        dpi=args.dpi,
        log_scale=args.log_scale,
        linthresh=args.linthresh,
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()

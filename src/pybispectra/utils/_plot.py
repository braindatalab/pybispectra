"""Private helper tools for plotting results."""

from abc import ABC, abstractmethod
from copy import deepcopy

from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import ScalarFormatter, StrMethodFormatter
import numpy as np

from pybispectra.utils._utils import _fast_find_first


class _PlotBase(ABC):
    """Base class for plotting results.

    Notes
    -----
    Does not check initialisation inputs, assuming these have been checked by
    the publicly-avaiable class/function.
    """

    def __init__(
        self,
        data: np.ndarray,
        indices: tuple,
        name: str,
    ) -> None:
        self._data = data.copy()
        self._indices = deepcopy(indices)

        if (
            len(indices) == 2
            and isinstance(indices[0], list)
            and isinstance(indices[1], list)
        ):
            self.n_nodes = len(indices[0])
        else:
            self.n_nodes = len(indices)

        self.name = deepcopy(name)

    @abstractmethod
    def plot(self) -> None:
        """Plot the results."""

    @abstractmethod
    def _sort_plot_inputs(
        self,
        nodes: list[int] | None,
        n_rows: int,
        n_cols: int,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
    ) -> list[int]:
        """Sort the plotting inputs.

        Returns
        -------
        nodes : list of int
        """
        if nodes is None:
            nodes = np.arange(self.n_nodes).tolist()
        if not isinstance(nodes, list) or not all(
            isinstance(con, int) for con in nodes
        ):
            raise TypeError("`nodes` must be a list of integers.")
        if any(con >= self.n_nodes for con in nodes) or any(
            con < 0 for con in nodes
        ):
            raise ValueError(
                "The requested node is not present in the results."
            )

        if not isinstance(n_rows, int) or not isinstance(n_cols, int):
            raise TypeError("`n_rows` and `n_cols` must be integers.")
        if n_rows < 1 or n_cols < 1:
            raise ValueError("`n_rows` and `n_cols` must be >= 1.")

        if not isinstance(
            major_tick_intervals, (int, float)
        ) or not isinstance(minor_tick_intervals, (int, float)):
            raise TypeError(
                "`major_tick_intervals` and `minor_tick_intervals` should be "
                "ints or floats."
            )
        if minor_tick_intervals >= major_tick_intervals:
            raise ValueError(
                "`major_tick_intervals` should be > `minor_tick_intervals`."
            )

        return nodes

    def _create_plots(
        self, nodes: list[int], n_rows: int, n_cols: int
    ) -> tuple[list[Figure], list[np.ndarray]]:
        """Create figures and subplots to fill with results.

        Returns
        -------
        figures : list of matplotlib Figure
            Figures for the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))``.

        axes : list of numpy.ndarray of matplotlib pyplot Axes
            Subplot axes for the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))`` where each entry is a 1D
            ``numpy.ndarray`` of length ``(n_rows * n_cols)``.
        """
        figures = []
        axes = []

        plot_n = 0
        for node_i in range(len(nodes)):
            if node_i == plot_n:
                fig, axs = plt.subplots(n_rows, n_cols, layout="constrained")
                figures.append(fig)
                if n_rows * n_cols > 1:
                    axs = np.ravel(axs)
                else:
                    axs = np.array([axs])
                axes.append(axs)
                plot_n += n_rows * n_cols
            if plot_n >= len(nodes):
                break

        return figures, axes

    @abstractmethod
    def _plot_results(self) -> None:
        """Plot results on the relevant figures/subplots."""

    @abstractmethod
    def _set_axis_ticks(self) -> None:
        """Set major and minor tick intervals of x- and y-axes."""


class _PlotCFC(_PlotBase):
    """Class for plotting cross-frequency coupling (CFC) results."""

    def __init__(
        self,
        data: np.ndarray,
        indices: tuple[list[int], list[int]],
        f1s: np.ndarray,
        f2s: np.ndarray,
        name: str,
    ) -> None:  # noqa D107
        super().__init__(data, indices, name)

        self.f1s = f1s.copy()
        self.f2s = f2s.copy()

    def plot(
        self,
        nodes: list[int] | None = None,
        f1s: np.ndarray | None = None,
        f2s: np.ndarray | None = None,
        n_rows: int = 1,
        n_cols: int = 1,
        major_tick_intervals: int | float = 5.0,
        minor_tick_intervals: int | float = 1.0,
        cbar_range: list[float] | tuple[list[float]] | None = None,
        show: bool = True,
    ) -> tuple[list[Figure], list[np.ndarray]]:
        """Plot the results.

        Parameters
        ----------
        nodes : list of int | None (default None)
            Indices of connections to plot. If ``None``, plot all connections.

        f1s : numpy.ndarray | None (default None)
            Low frequencies of the results to plot. If ``None``, plot all low
            frequencies.

        f2s : numpy.ndarray | None (default None)
            High frequencies of the results to plot. If ``None``, plot all high
            frequencies.

        n_rows : int (default ``1``)
            Number of rows of subplots per figure.

        n_cols : int (default ``1``)
            Number of columns of subplots per figure.

        major_tick_intervals : int | float (default ``5.0``)
            Intervals (in Hz) at which the major ticks of the x- and y-axes
            should occur.

        minor_tick_intervals : int | float (default ``1.0``)
            Intervals (in Hz) at which the minor ticks of the x- and y-axes
            should occur.

        cbar_range : list of float | tuple of list of float | None (default ``None``)
            Range (in units of the data) for the colourbars, consisting of the
            lower and upper limits, respectively. If ``None``, the range is
            computed automatically. If a list of float, this range is used for
            all plots. If a tuple of list of float, the ranges are used for
            each individual plot.

        show : bool (default ``True``)
            Whether or not to show the plotted results.

        Returns
        -------
        figures : list of matplotlib Figure
            Figures of the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))``.

        axes : list of numpy.ndarray of matplotlib pyplot Axes
            Subplot axes for the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))`` where each entry is a 1D
            ``numpy.ndarray`` of length ``(n_rows * n_cols)``.

        Notes
        -----
        ``n_rows`` and ``n_cols`` of ``1`` will plot the results for each
        connection on a new figure.
        """
        nodes, f1s, f2s, f1_idcs, f2_idcs, cbar_range = self._sort_plot_inputs(
            nodes,
            f1s,
            f2s,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
            cbar_range,
        )
        figures, axes = self._create_plots(nodes, n_rows, n_cols)
        self._plot_results(
            figures,
            axes,
            nodes,
            f1s,
            f2s,
            f1_idcs,
            f2_idcs,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
            cbar_range,
        )

        if show:
            plt.show()

        return figures, axes

    def _sort_plot_inputs(
        self,
        nodes: list[int] | None,
        f1s: np.ndarray | None,
        f2s: np.ndarray | None,
        n_rows: int,
        n_cols: int,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
        cbar_range: list[float] | tuple[list[float]] | None,
    ) -> tuple[
        list[int],
        np.ndarray,
        np.ndarray,
        list[int],
        list[int],
        tuple[list[float | None]],
    ]:
        """Sort the plotting inputs.

        Returns
        -------
        nodes : list of int

        f1s : numpy.ndarray of float

        f2s : numpy.ndarray of float

        f1_idcs : list of int
            Indices of ``f1s`` in the results.

        f2_idcs : list of int
            Indices of ``f2s`` in the results.

        cbar_range : tuple of list of float or None
        """
        nodes = super()._sort_plot_inputs(
            nodes,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
        )

        if f1s is None:
            f1s = self.f1s.copy()
        if f2s is None:
            f2s = self.f2s.copy()
        if not isinstance(f1s, np.ndarray) or not isinstance(f2s, np.ndarray):
            raise TypeError("`f1s` and `f2s` must be NumPy arrays.")
        if f1s.ndim != 1 or f2s.ndim != 1:
            raise ValueError("`f1s` and `f2s` must be 1D arrays.")
        if any(freq not in self.f1s for freq in f1s) or any(
            freq not in self.f2s for freq in f2s
        ):
            raise ValueError(
                "Entries of `f1s` and `f2s` must be present in the results."
            )
        f1_idcs = [_fast_find_first(self.f1s, freq) for freq in f1s]
        f2_idcs = [_fast_find_first(self.f2s, freq) for freq in f2s]

        if not isinstance(cbar_range, (list, tuple, type(None))):
            raise TypeError("`cbar_range` must be a list, tuple, or None.")
        if isinstance(cbar_range, tuple):
            if len(cbar_range) != len(nodes):
                raise ValueError(
                    "If `cbar_range` is a tuple, one entry must be provided "
                    "for each node being plotted."
                )
        else:
            fill = cbar_range if cbar_range is not None else [None, None]
            cbar_range = [fill for _ in range(len(nodes))]
        for entry in cbar_range:
            if len(entry) != 2:
                raise ValueError(
                    "Limits in `cbar_range` must have length of 2."
                )

        return nodes, f1s, f2s, f1_idcs, f2_idcs, cbar_range

    def _plot_results(
        self,
        figures: list[Figure],
        axes: list[np.ndarray],
        nodes: list[int],
        f1s: np.ndarray,
        f2s: np.ndarray,
        f1_idcs: list[int],
        f2_idcs: list[int],
        n_rows: int,
        n_cols: int,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
        cbar_range: tuple[list[float | None]],
    ) -> None:
        """Plot results on the relevant figures/subplots."""
        fig_i = 0
        plot_n = 0
        fig_plot_n = 0
        while fig_i < len(figures):
            for _ in range(n_rows):
                for _ in range(n_cols):
                    node_i = nodes[plot_n]
                    axis = axes[fig_i][fig_plot_n]

                    mesh = axis.pcolormesh(
                        f1s,
                        f2s,
                        self._data[node_i][np.ix_(f1_idcs, f2_idcs)].T,
                        vmin=cbar_range[plot_n][0],
                        vmax=cbar_range[plot_n][1],
                    )

                    plt.colorbar(
                        mesh, ax=axis, label="Coupling (A.U.)", shrink=0.3
                    )

                    axis.set_aspect("equal")
                    self._set_axis_ticks(
                        axis,
                        major_tick_intervals,
                        minor_tick_intervals,
                    )
                    axis.grid(
                        which="major",
                        axis="both",
                        linestyle="--",
                        color=[0.7, 0.7, 0.7],
                        alpha=0.7,
                    )
                    axis.set_xlabel("$f_1$ (Hz)")
                    axis.set_ylabel("$f_2$ (Hz)")

                    axis.set_title(
                        f"Seed: {self._indices[0][node_i]} | Target: "
                        f"{self._indices[1][node_i]}"
                    )

                    plot_n += 1
                    fig_plot_n += 1
                    if fig_plot_n >= n_rows * n_cols:
                        figures[fig_i].suptitle(self.name)
                        fig_plot_n = 0
                        fig_i += 1

    def _set_axis_ticks(
        self,
        axis: plt.Axes,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
    ) -> None:
        """Set major and minor tick intervals of x- and y-axes."""
        axis.xaxis.set_major_locator(plt.MultipleLocator(major_tick_intervals))
        axis.xaxis.set_minor_locator(plt.MultipleLocator(minor_tick_intervals))
        axis.yaxis.set_major_locator(plt.MultipleLocator(major_tick_intervals))
        axis.yaxis.set_minor_locator(plt.MultipleLocator(minor_tick_intervals))


class _PlotTDE(_PlotBase):
    """Class for plotting time-delay estimation (TDE) results."""

    def __init__(
        self,
        data: np.ndarray,
        tau: tuple[float],
        indices: tuple[list[int], list[int]],
        times: np.ndarray,
        name: str,
    ) -> None:  # noqa D107
        super().__init__(data, indices, name)

        self.tau = deepcopy(tau)
        self.times = times.copy()

    def plot(
        self,
        nodes: list[int] | None = None,
        times: list[float] | None = None,
        n_rows: int = 1,
        n_cols: int = 1,
        major_tick_intervals: int | float = 500.0,
        minor_tick_intervals: int | float = 100.0,
        show: bool = True,
    ) -> tuple[list[Figure], list[np.ndarray]]:
        """Plot the results.

        Parameters
        ----------
        nodes : list of int | None (default None)
            Indices of connections to plot. If ``None``, plot all connections.

        times : list of float | None (default None)
            Start and end times of the results to plot, respectively. If
            ``None``, all times are plotted.

        f1s : numpy.ndarray | None (default None)
            Times of the results to plot. If ``None``, all times are plotted.

        n_rows : int (default ``1``)
            Number of rows of subplots per figure.

        n_cols : int (default ``1``)
            Number of columns of subplots per figure.

        major_tick_intervals : int | float (default ``500.0``)
            Intervals (in ms) at which the major ticks of the x- and y-axes
            should occur.

        minor_tick_intervals : int | float (default ``100.0``)
            Intervals (in ms) at which the minor ticks of the x- and y-axes
            should occur.

        show : bool (default ``True``)
            Whether or not to show the plotted results.

        Returns
        -------
        figures : list of matplotlib Figure
            Figures of the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))``.

        axes : list of numpy.ndarray of matplotlib pyplot Axes
            Subplot axes for the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))`` where each entry is a 1D
            ``numpy.ndarray`` of length ``(n_rows * n_cols)``.

        Notes
        -----
        ``n_rows`` and ``n_cols`` of ``1`` will plot the results for each
        connection on a new figure.
        """
        nodes, times, time_idcs = self._sort_plot_inputs(
            nodes,
            times,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
        )
        figures, axes = self._create_plots(nodes, n_rows, n_cols)
        self._plot_results(
            figures,
            axes,
            nodes,
            times,
            time_idcs,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
        )

        if show:
            plt.show()

        return figures, axes

    def _sort_plot_inputs(
        self,
        nodes: list[int] | None,
        times: list[float] | None,
        n_rows: int,
        n_cols: int,
        major_tick_intervals: float,
        minor_tick_intervals: float,
    ) -> tuple[list[int], np.ndarray, list[int]]:
        """Sort the plotting inputs.

        Returns
        -------
        nodes : list of int

        times : numpy ndarray
            Times of the results to plot nearest to the requested times.

        time_idcs : list of int
            Indices of ``times`` in the results.
        """
        nodes = super()._sort_plot_inputs(
            nodes,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
        )

        time_idcs = None
        if times is None:
            time_idcs = [0, self.times.shape[0] - 1]
        else:
            if not isinstance(times, list):
                raise TypeError("`times` must be a list of float.")
            if len(times) != 2:
                raise ValueError("`times` must have a length of two.")
        if time_idcs is None:
            time_idcs = [np.abs(self.times - time).argmin() for time in times]
        times = self.times[time_idcs[0] : time_idcs[1] + 1]

        return nodes, times, time_idcs

    def _plot_results(
        self,
        figures: list[Figure],
        axes: list[np.ndarray],
        nodes: list[int],
        times: np.ndarray,
        time_idcs: list[int],
        n_rows: int,
        n_cols: int,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
    ) -> None:
        """Plot results on the relevant figures/subplots."""
        fig_i = 0
        plot_n = 0
        fig_plot_n = 0
        while fig_i < len(figures):
            for _ in range(n_rows):
                for _ in range(n_cols):
                    node_i = nodes[plot_n]
                    axis = axes[fig_i][fig_plot_n]

                    axis.plot(
                        times,
                        self._data[node_i][time_idcs[0] : time_idcs[1] + 1],
                    )

                    self._mark_delay(
                        axis,
                        times,
                        self.tau[node_i],
                        self._data[node_i][time_idcs[0] : time_idcs[1] + 1],
                    )

                    self._set_axis_ticks(
                        axis, major_tick_intervals, minor_tick_intervals
                    )
                    axis.grid(
                        which="major",
                        axis="x",
                        linestyle="-",
                        color=[0.7, 0.7, 0.7],
                        alpha=0.7,
                    )
                    axis.set_xlabel("Time (ms)")
                    axis.set_ylabel("Estimate strength (A.U.)")

                    axis.set_title(
                        f"Seed: {self._indices[0][node_i]} | Target: "
                        f"{self._indices[1][node_i]}"
                    )

                    plot_n += 1
                    fig_plot_n += 1
                    if fig_plot_n >= n_rows * n_cols:
                        figures[fig_i].suptitle(self.name)
                        fig_plot_n = 0
                        fig_i += 1

    def _mark_delay(
        self,
        axis: plt.Axes,
        times: np.ndarray,
        tau: float,
        results: np.ndarray,
    ) -> None:
        """Mark estimated delay on the plot."""
        if tau not in times:
            xlim = axis.get_xlim()
            ylim = axis.get_ylim()
            xrange = xlim[1] - xlim[0]
            yrange = ylim[1] - ylim[0]
            annot_xy = ((xrange / 2) + xlim[0], ylim[1] - yrange * 0.05)
            alignment = "center"
        else:
            tau_idx = np.where(times == tau)[0][0]
            annot_xy = (tau, results[tau_idx])
            alignment = "left"
        axis.annotate(f"$\\tau$ = {tau:.2f} ms", xy=annot_xy, ha=alignment)

    def _set_axis_ticks(
        self,
        axis: plt.Axes,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
    ) -> None:
        """Set major and minor tick intervals of the x-axis."""
        axis.xaxis.set_major_locator(plt.MultipleLocator(major_tick_intervals))
        axis.xaxis.set_minor_locator(plt.MultipleLocator(minor_tick_intervals))


class _PlotWaveShape(_PlotBase):
    """Class for plotting wave shape results."""

    def __init__(
        self,
        data: np.ndarray,
        indices: tuple[list[int], list[int]],
        f1s: np.ndarray,
        f2s: np.ndarray,
        name: str,
    ) -> None:  # noqa D107
        super().__init__(data, indices, name)

        self.f1s = f1s.copy()
        self.f2s = f2s.copy()

    def plot(
        self,
        nodes: list[int] | None = None,
        f1s: np.ndarray | None = None,
        f2s: np.ndarray | None = None,
        n_rows: int = 1,
        n_cols: int = 1,
        major_tick_intervals: int | float = 5.0,
        minor_tick_intervals: int | float = 1.0,
        cbar_range_abs: list[float] | tuple[list[float]] | None = None,
        cbar_range_real: list[float] | tuple[list[float]] | None = None,
        cbar_range_imag: list[float] | tuple[list[float]] | None = None,
        cbar_range_phase: list[float] | tuple[list[float]] | None = None,
        show: bool = True,
    ) -> tuple[list[Figure], list[np.ndarray]]:
        """Plot the results.

        Parameters
        ----------
        nodes : list of int | None (default None)
            Indices of channels to plot. If ``None``, plot all channels.

        f1s : numpy.ndarray | None (default None)
            Low frequencies of the results to plot. If ``None``, plot all low
            frequencies.

        f2s : numpy.ndarray | None (default None)
            High frequencies of the results to plot. If ``None``, plot all high
            frequencies.

        n_rows : int (default ``1``)
            Number of rows of subplots per figure.

        n_cols : int (default ``1``)
            Number of columns of subplots per figure.

        major_tick_intervals : int | float (default ``5.0``)
            Intervals (in Hz) at which the major ticks of the x- and y-axes
            should occur.

        minor_tick_intervals : int | float (default ``1.0``)
            Intervals (in Hz) at which the minor ticks of the x- and y-axes
            should occur.

        cbar_range_abs : list of float | tuple of list of float | None (default ``None``)
            Range (in units of the data) for the colourbars of the absolute
            value of the results, consisting of the lower and upper limits,
            respectively. If ``None``, the range is computed automatically. If
            a list of float, this range is used for all plots. If a tuple of
            list of float, the ranges are used for each individual plot. Note
            that results should be limited to the range [0, 1].

        cbar_range_real : list of float | tuple of list of float | None (default ``None``)
            Range (in units of the data) for the colourbars of the real value
            of the results, consisting of the lower and upper limits,
            respectively. If ``None``, the range is computed automatically. If
            a list of float, this range is used for all plots. If a tuple of
            list of float, the ranges are used for each individual plot. Note
            that results should be limited to the range [-1, 1].

        cbar_range_imag : list of float | tuple of list of float | None (default ``None``)
            Range (in units of the data) for the colourbars of the imaginary
            value of the results, consisting of the lower and upper limits,
            respectively. If ``None``, the range is computed automatically. If
            a list of float, this range is used for all plots. If a tuple of
            list of float, the ranges are used for each individual plot. Note
            that results should be limited to the range [-1, 1].

        cbar_range_phase : list of float | tuple of list of float | None (default ``None``)
            Range (in units of the data) for the colourbars of the phase of the
            results, consisting of the lower and upper limits, respectively. If
            ``None``, the range is computed automatically. If a list of float,
            this range is used for all plots. If a tuple of list of float, the
            ranges are used for each individual plot. Note that results should
            be limited to the range (-pi, pi].

        show : bool (default ``True``)
            Whether or not to show the plotted results.

        Returns
        -------
        figures : list of matplotlib Figure
            Figures of the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))``.

        axes : list of numpy.ndarray of matplotlib pyplot Axes
            Subplot axes for the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))`` where each entry is a 1D
            ``numpy.ndarray`` of length ``(n_rows * n_cols)``.

        Notes
        -----
        ``n_rows`` and ``n_cols`` of ``1`` will plot the results for each
        connection on a new figure.
        """  # noqa: E501
        (
            nodes,
            f1s,
            f2s,
            f1_idcs,
            f2_idcs,
            cbar_ranges,
        ) = self._sort_plot_inputs(
            nodes,
            f1s,
            f2s,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
            cbar_range_abs,
            cbar_range_real,
            cbar_range_imag,
            cbar_range_phase,
        )
        figures, subfigures, axes = self._create_plots(nodes, n_rows, n_cols)
        self._plot_results(
            figures,
            subfigures,
            axes,
            nodes,
            f1s,
            f2s,
            f1_idcs,
            f2_idcs,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
            cbar_ranges,
        )

        if show:
            plt.show()

        return figures, axes

    def _sort_plot_inputs(
        self,
        nodes: list[int] | None,
        f1s: np.ndarray | None,
        f2s: np.ndarray | None,
        n_rows: int,
        n_cols: int,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
        cbar_range_abs: list[float] | tuple[list[float]] | None,
        cbar_range_real: list[float] | tuple[list[float]] | None,
        cbar_range_imag: list[float] | tuple[list[float]] | None,
        cbar_range_phase: list[float] | tuple[list[float]] | None,
    ) -> tuple[
        list[int],
        np.ndarray,
        np.ndarray,
        list[int],
        list[int],
        list[tuple[list[float | None]]],
    ]:
        """Sort the plotting inputs.

        Returns
        -------
        nodes : list of int

        f1s : numpy.ndarray of float

        f2s : numpy.ndarray of float

        f1_idcs : list of int
            Indices of ``f1s`` in the results.

        f2_idcs : list of int
            Indices of ``f2s`` in the results.

        cbar_ranges : list of tuple of list of float or None
            Colourbar ranges for the absolute, real, imaginary, and phase
            plots, respectively.
        """
        nodes = super()._sort_plot_inputs(
            nodes,
            n_rows,
            n_cols,
            major_tick_intervals,
            minor_tick_intervals,
        )

        if f1s is None:
            f1s = self.f1s.copy()
        if f2s is None:
            f2s = self.f2s.copy()
        if not isinstance(f1s, np.ndarray) or not isinstance(f2s, np.ndarray):
            raise TypeError("`f1s` and `f2s` must be NumPy arrays.")
        if f1s.ndim != 1 or f2s.ndim != 1:
            raise ValueError("`f1s` and `f2s` must be 1D arrays.")
        if any(freq not in self.f1s for freq in f1s) or any(
            freq not in self.f2s for freq in f2s
        ):
            raise ValueError(
                "Entries of `f1s` and `f2s` must be present in the results."
            )
        f1_idcs = [_fast_find_first(self.f1s, freq) for freq in f1s]
        f2_idcs = [_fast_find_first(self.f2s, freq) for freq in f2s]

        cbar_ranges = [
            cbar_range_abs,
            cbar_range_real,
            cbar_range_imag,
            cbar_range_phase,
        ]
        cbar_names = ["abs", "real", "imag", "phase"]
        cbar_idx = 0
        for cbar_range, cbar_name in zip(
            cbar_ranges,
            cbar_names,
        ):
            if not isinstance(cbar_range, (list, tuple, type(None))):
                raise TypeError(
                    f"`cbar_range_{cbar_name}` must be a list, tuple, or None."
                )
            if isinstance(cbar_range, tuple):
                if len(cbar_range) != len(nodes):
                    raise ValueError(
                        f"If `cbar_range_{cbar_name}` is a tuple, one entry "
                        "must be provided for each node being plotted."
                    )
            else:
                fill = cbar_range if cbar_range is not None else [None, None]
                cbar_range = [fill for _ in range(len(nodes))]
            for entry in cbar_range:
                if len(entry) != 2:
                    raise ValueError(
                        f"Limits in `cbar_range_{cbar_name}` must have length "
                        "of 2."
                    )
            cbar_ranges[cbar_idx] = cbar_range
            cbar_idx += 1

        return (nodes, f1s, f2s, f1_idcs, f2_idcs, cbar_ranges)

    def _create_plots(
        self, nodes: list[int], n_rows: int, n_cols: int
    ) -> tuple[list[Figure], list[np.ndarray]]:
        """Create figures and subplots to fill with results.

        Returns
        -------
        figures : list of matplotlib Figure
            Figures for the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))``.

        subfigures : list of matplotlib Figure
            Subfigures for the results in a list of length ``figures``.

        axes : list of numpy.ndarray of matplotlib pyplot Axes
            Subplot axes for the results in a list of length
            ``ceil(n_nodes / (n_rows * n_cols))`` where each entry is a 1D
            ``numpy.ndarray`` of length ``(n_rows * n_cols)``.
        """
        figures = []
        subfigures = []
        axes = []

        plot_n = 0
        for node_i in range(len(nodes)):
            if node_i == plot_n:
                fig = plt.figure(layout="compressed")
                figures.append(fig)
                subfigs = fig.subfigures(
                    n_rows, n_cols, wspace=0.05, hspace=0.05
                )
                if n_rows * n_cols > 1:
                    subfigs = np.ravel(subfigs)
                else:
                    subfigs = np.array([subfigs])
                subfigures.append(subfigs)
                subfig_axs = []
                for subfig in subfigs:
                    axs = np.ravel(subfig.subplots(2, 2))
                    subfig_axs.append(axs)
                axes.append(subfig_axs)
                plot_n += n_rows * n_cols
            if plot_n >= len(nodes):
                break

        return figures, subfigures, axes

    def _plot_results(
        self,
        figures: list[Figure],
        subfigures: list[np.ndarray],
        axes: list[np.ndarray],
        nodes: list[int],
        f1s: np.ndarray,
        f2s: np.ndarray,
        f1_idcs: list[int],
        f2_idcs: list[int],
        n_rows: int,
        n_cols: int,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
        cbar_ranges: list[tuple[list[float | None]]],
    ) -> None:
        """Plot results on the relevant figures/subplots."""
        fig_i = 0
        plot_n = 0
        fig_plot_n = 0
        while fig_i < len(figures):
            for _ in range(n_rows):
                for _ in range(n_cols):
                    node_i = nodes[plot_n]
                    subfig = subfigures[fig_i][fig_plot_n]

                    data_funcs = [np.abs, np.real, np.imag, np.angle]
                    axes_titles = ["Absolute", "Real", "Imaginary", "Phase"]
                    cmaps = [
                        "viridis",
                        "viridis",
                        "viridis",
                        "twilight_shifted",
                    ]
                    cbar_titles = [
                        "Magnitude (A.U.)",
                        "Magnitude (A.U.)",
                        "Magnitude (A.U.)",
                        "Phase (radians)",
                    ]
                    for (
                        axis,
                        data_func,
                        axis_title,
                        cmap,
                        cbar_title,
                        cbar_range,
                    ) in zip(
                        axes[fig_i][fig_plot_n],
                        data_funcs,
                        axes_titles,
                        cmaps,
                        cbar_titles,
                        cbar_ranges,
                    ):
                        data = data_func(
                            self._data[node_i][np.ix_(f1_idcs, f2_idcs)].T
                        )

                        if axis_title == "Phase":
                            data /= np.pi  # normalise to (-1, 1]
                            format_ = StrMethodFormatter(r"{x} $\pi$")
                        else:
                            format_ = ScalarFormatter()

                        mesh = axis.pcolormesh(
                            f1s,
                            f2s,
                            data,
                            cmap=cmap,
                            vmin=cbar_range[plot_n][0],
                            vmax=cbar_range[plot_n][1],
                        )

                        plt.colorbar(
                            mesh,
                            ax=axis,
                            label=cbar_title,
                            shrink=0.5,
                            format=format_,
                            panchor=False,
                        )

                        axis.set_title(axis_title)
                        axis.set_aspect("equal")
                        self._set_axis_ticks(
                            axis,
                            major_tick_intervals,
                            minor_tick_intervals,
                        )
                        axis.grid(
                            which="major",
                            axis="both",
                            linestyle="--",
                            color=[0.7, 0.7, 0.7],
                            alpha=0.7,
                        )
                        axis.set_xlabel("$f_1$ (Hz)")
                        axis.set_ylabel("$f_2$ (Hz)")

                    subfig.suptitle(f"Channel: {self._indices[node_i]}")

                    plot_n += 1
                    fig_plot_n += 1
                    if fig_plot_n >= n_rows * n_cols:
                        figures[fig_i].suptitle(self.name)
                        fig_plot_n = 0
                        fig_i += 1

    def _set_axis_ticks(
        self,
        axis: plt.Axes,
        major_tick_intervals: int | float,
        minor_tick_intervals: int | float,
    ) -> None:
        """Set major and minor tick intervals of x- and y-axes."""
        axis.xaxis.set_major_locator(plt.MultipleLocator(major_tick_intervals))
        axis.xaxis.set_minor_locator(plt.MultipleLocator(minor_tick_intervals))
        axis.yaxis.set_major_locator(plt.MultipleLocator(major_tick_intervals))
        axis.yaxis.set_minor_locator(plt.MultipleLocator(minor_tick_intervals))

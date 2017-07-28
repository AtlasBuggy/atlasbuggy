"""
The base class shared by liveplotter and staticplotter. Contains properties shared by the two types.
"""

import matplotlib.gridspec as gridspec
import numpy as np
from ..plotters.plot import RobotPlot
from ..plotters.collection import RobotPlotCollection


class BasePlotter:
    fig_num = 0

    def __init__(self, num_columns, legend_args, draw_legend, matplotlib_events, enabled, fig_args, fig_kwargs,
                 *robot_plots):
        """
        A plotter is one matplotlib figure. Having multiple robot plots creates subplots
        :param num_columns: Configure how the subplots are arranged
        :param legend_args: dictionary of arguments to pass to plt.legend
        :param draw_legend: puts a legend on the plot
        :param matplotlib_events: dictionary of matplotlib callback events
            key: event name (string), value: function reference
        :param enabled: enable or disable plot
        :param robot_plots: RobotPlot or RobotPlotCollection instances. Each one will be a subplot
        """

        self.enabled = enabled
        self.robot_plots = []
        for plot in robot_plots:
            if plot.enabled:  # only append plot if it is enabled
                self.robot_plots.append(plot)

        # if self.enabled:  # if plotter is enabled check if all the plots are enabled
        #     if len(self.robot_plots) == 0:
        #         self.enabled = False
        #     else:
        #         self.enabled = True

        self.legend_args = legend_args
        if self.legend_args is None:
            self.legend_args = {}

        self.enable_legend = draw_legend

        self.has_updated = True

        self.plt = None

        self.axes = {}
        self.lines = {}
        self.plots = {}
        self.extra_elements = {}

        self.num_plots = 0
        self.num_rows = 0
        self.num_columns = 0

        if self.enabled:
            self.open_matplotlib()  # launch the python app only if the plotter is used
            if fig_args is None:
                fig_args = tuple()
            if fig_kwargs is None:
                fig_kwargs = dict()
            self.fig = self.plt.figure(BasePlotter.fig_num, *fig_args, **fig_kwargs)
            BasePlotter.fig_num += 1

            # link matplotlib events
            if matplotlib_events is not None:
                for event_name in matplotlib_events:
                    self.fig.canvas.mpl_connect(event_name, matplotlib_events[event_name])

            self.num_columns = num_columns

            self._adjust_grid(self.num_columns, len(self.robot_plots))

            # create subplots for each robot plot
            for plot_num, plot in enumerate(self.robot_plots):
                self._create_subplot(plot, plot_num + 1)
        else:  # disable all plots if plotter is disabled
            for plot in self.robot_plots:
                plot.enabled = False

    def update_collection(self, plot):
        pass

    def _create_lines(self, plot):
        pass

    def add_plots(self, *robot_plots, num_columns=None):
        pass

    def set_time(self, start_time=None):
        pass

    def plot(self):
        pass

    def _create_subplot(self, plot, plot_num):
        self.plots[plot.name] = plot
        if plot.flat:
            self.axes[plot.name] = self.fig.add_subplot(self.num_rows, self.num_columns, plot_num)
        else:
            self.axes[plot.name] = self.fig.add_subplot(self.num_rows, self.num_columns, plot_num, projection='3d')

        self.axes[plot.name].set_title(plot.name)

    def _adjust_grid(self, num_columns, num_plots):
        # based on number of columns and plot number, get the number of rows
        if num_plots > 0:
            self.num_plots = num_plots
            if num_columns is not None:
                self.num_columns = num_columns
            if self.num_plots < self.num_columns:
                self.num_columns = self.num_plots
            self.num_rows = self.num_plots // self.num_columns
            self.num_rows += self.num_plots % self.num_columns

    def add_subplots(self, *new_plots, num_columns=None):
        self._adjust_grid(num_columns, len(new_plots) + self.num_plots)

        grid = gridspec.GridSpec(self.num_rows, self.num_columns)
        for plot_num, plot in enumerate(self.robot_plots):
            self.axes[plot.name].set_position(grid[plot_num].get_position(self.fig))

        for plot_num, plot in enumerate(new_plots):
            self._create_subplot(plot, plot_num + 1 + len(self.robot_plots))

        self.robot_plots.extend(new_plots)
        self.update_legend()

    def open_matplotlib(self):
        from matplotlib import pyplot
        self.plt = pyplot

    def init_legend(self):
        """
        Create a legend. Static and live plots need them created at different times
        """
        if self.enable_legend and self.enabled:
            # set defaults
            if "fontsize" not in self.legend_args:  # small font
                self.legend_args["fontsize"] = 'x-small'
            if "shadow" not in self.legend_args:  # shadow
                self.legend_args["shadow"] = 'True'
            if "loc" not in self.legend_args:  # dynamic legend placement
                self.legend_args["loc"] = 0

            # self.plt.legend()
            self.update_legend()

    def update_legend(self):
        # draw_legend = True
        # if len(self.robot_plots) == 0:
        #     draw_legend = False
        # else:
        #     for plot in self.robot_plots:
        #         if isinstance(plot, RobotPlotCollection):
        #             if len(plot.plots) == 0:
        #                 draw_legend = False
        # if draw_legend:

        # tried to make legend warning go away. Not calling this at all causes weird things to happen
        if len(self.robot_plots) > 0:
            self.axes[list(self.axes.keys())[0]].legend(**self.legend_args)

    def _get_name(self, arg):
        """
        Interpret argument into the name of a plot (for internal use)
        :param arg: string or robot plot
        :return: name of the plot
        """
        if type(arg) == str:
            if arg in self.robot_plots and self.robot_plots[arg].enabled:
                return arg
            else:
                return None
        elif isinstance(arg, RobotPlot) or isinstance(arg, RobotPlotCollection):
            if arg.enabled:
                return arg.name
            else:
                return None
        else:
            raise ValueError("Invalid argument for _get_name: '%s'" % str(arg))

    def get_axis(self, arg):
        """
        Get the matplotlib axis based on the arg
        :param arg: string or robot plot
        :return: matplotlib axis instance
        """
        if self.enabled:
            plot_name = self._get_name(arg)

            if plot_name in self.axes.keys():
                return self.axes[plot_name]
        return None

    def draw_dot(self, arg, x, y, z=None, **dot_properties):
        """
        Draw a dot on the input plot (plot name or plot instance)
        :param arg: string or robot plot
        :param x: float
        :param y: float
        :param z: float
        :param dot_properties: matplotlib properties (color, markersize, etc)
        """
        if self.enabled:
            self.has_updated = True

            plot_name = self._get_name(arg)
            if plot_name is None:
                return

            if plot_name in self.axes.keys():
                if self.plots[plot_name].flat:
                    self.axes[plot_name].plot(x, y, 'o', **dot_properties)
                else:
                    self.axes[plot_name].plot([x], [y], [z], 'o', **dot_properties)

    def draw_image(self, plot, image, skew_coords=None, img_format=None, *imshow_args, **imshow_kwargs):
        """
        Draw a dot on the input plot (plot name or plot instance)
        """
        if self.enabled:
            self.has_updated = True

            plot_name = self._get_name(plot)
            if plot_name is None:
                return
            image_artist = self.plots[plot_name].image_artist

            if type(image) == str:
                if img_format is None:
                    img_format = "png"
                image = self.plt.imread(image, format=img_format)

            if skew_coords is not None:
                img_coord_1, img_coord_2, plot_coord_1, plot_coord_2 = skew_coords
                height, width = image.shape[0:2]
                img_x1 = height - img_coord_1[1]
                img_x2 = height - img_coord_2[1]
                img_y1 = width - img_coord_1[0]
                img_y2 = width - img_coord_2[0]
                height, width = width, height

                plot_x1 = (plot_coord_1[0] - plot_coord_2[0]) / (img_x1 - img_x2) * (0 - img_x2) + plot_coord_2[0]
                plot_x2 = (plot_coord_1[0] - plot_coord_2[0]) / (img_x1 - img_x2) * (width - img_x2) + plot_coord_2[0]
                plot_y1 = (plot_coord_1[1] - plot_coord_2[1]) / (img_y1 - img_y2) * (0 - img_y2) + plot_coord_2[1]
                plot_y2 = (plot_coord_1[1] - plot_coord_2[1]) / (img_y1 - img_y2) * (height - img_y2) + plot_coord_2[1]
                image = np.rot90(image, k=3)

                if image_artist is None:
                    self.plots[plot_name].image_artist = \
                        self.axes[plot_name].imshow(image, extent=(plot_x1, plot_x2, plot_y1, plot_y2),
                                                    *imshow_args, **imshow_kwargs)
                else:
                    self.plots[plot_name].image_artist.set_data(image)
            else:
                if image_artist is None:
                    self.plots[plot_name].image_artist = \
                        self.axes[plot_name].imshow(image, *imshow_args, **imshow_kwargs)
                else:
                    self.plots[plot_name].image_artist.set_data(image)

    def draw_text(self, arg, text, x, y, z=None, text_name=None, **text_properties):
        """
        Draw text on the input plot (plot name or plot instance)
        Text elements get put in extra_elements for reference later. If you want to override the
        previously drawn text, give the textbox a unique name.

        :param arg: string or robot plot
        :param text: string
        :param x: float
        :param y: float
        :param z: float
        :param text_name: a unique name
        :param text_properties: color, font, etc.
        """
        if self.enabled:
            self.has_updated = True

            plot_name = self._get_name(arg)
            if plot_name is None:
                return

            if plot_name in self.axes.keys():
                if text_name is not None and text_name in self.extra_elements:
                    self.extra_elements[text_name].remove()
                if self.plots[plot_name].flat:
                    self.extra_elements[text_name] = self.axes[plot_name].text(x, y, text, **text_properties)
                else:
                    self.extra_elements[text_name] = self.axes[plot_name].text([x], [y], [z], text, **text_properties)

    def set_line_props(self, arg, **kwargs):
        """
        Change the properties of a plot (color, markersize, etc.)

        :param arg: string or robot plot
        :param kwargs: properties to change
        """
        if self.enabled:
            self.has_updated = True

            plot_name = self._get_name(arg)
            if plot_name is None:
                return

            if isinstance(arg, RobotPlot) and arg.collection_plot is not None:
                collection_name = arg.collection_plot.name
                self.lines[collection_name][plot_name].set(**kwargs)
            else:
                self.lines[plot_name].set(**kwargs)

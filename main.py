import multiprocessing
import os
from functools import partial
from os.path import basename
from tkinter import Tk, messagebox, filedialog

import laspy
import numpy as np
import dearpygui.dearpygui as dpg

import config


def classification_split(classification, classes, classes_to_skip, class_id):
    if class_id in classes_to_skip:
        return None

    new_classification = []
    for i, class_to_write in enumerate(classification):
        if class_to_write in classes:
            new_classification.append(class_to_write)
        else:
            new_classification.append(1)

    return [class_id, new_classification]


def split_las(output, path, classes, classes_to_skip):
    las_file = laspy.read(path)
    classification = las_file.classification
    file_name, file_extension = os.path.splitext(basename(path))
    output_path = os.path.join(output, os.path.basename(file_name))
    os.makedirs(output_path, exist_ok=True)

    unique_classes = [class_id for class_id in np.unique(classification) if class_id not in classes_to_skip]
    pool = multiprocessing.Pool(processes=int(multiprocessing.cpu_count() / 2))
    results = []
    for job in pool.imap_unordered(
        partial(classification_split, classification, classes, classes_to_skip),
        unique_classes,
    ):
        results.append(job)
        print(dpg.get_value("progress_bar"))
        dpg.set_value("progress_bar", dpg.get_value("progress_bar") + 1/len(unique_classes))

    pool.close()

    for i, result in enumerate(results):
        if result:
            save_path = os.path.join(
                output_path, f"{file_name}_{result[0]}{file_extension}"
            )
            print(f"Writing class file {save_path}")
            new_classification = result[1]
            las_file.classification = new_classification
            las_file.write(save_path)


def run(path: str, output_path: str, classes: str, classes_to_skip: str):
    root = Tk()
    root.withdraw()
    if not path:
        messagebox.showerror("Error", "You need to specify an input path")
        return

    if not output_path:
        messagebox.showerror("Error", "You need to specify an output path")
        return

    try:
        classes = [int(x) for x in classes.split(",")]
    except ValueError:
        messagebox.showerror(
            "Error", "Classes must be a comma separated list of integers"
        )
        return

    try:
        classes_to_skip = [int(x) for x in classes_to_skip.split(",")]
    except ValueError:
        messagebox.showerror(
            "Error", "Classes to skip must be a comma separated list of integers"
        )
        return

    print(f"Input path: {path}")
    print(f"Output path: {output_path}")
    print(f"Classes to left in each file: {classes}")
    print(f"Classes to skip: {classes_to_skip}")

    if not os.path.exists(path):
        messagebox.showerror("Error", "Input path does not exist")
        return

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    files = [
        os.path.join(path, file)
        for file in os.listdir(path)
        if file.endswith((".las", ".laz"))
    ]

    if not files:
        messagebox.showerror("Error", "No .las/.laz files found")
        return

    dpg.set_value("progress_bar", 0)
    dpg.show_item("progress_bar")
    dpg.hide_item("Run")
    for file in files:
        split_las(output_path, file, classes, classes_to_skip)
    dpg.hide_item("progress_bar")
    dpg.show_item("Run")


def browse_files(tag: str):
    root = Tk()
    root.withdraw()

    path = filedialog.askdirectory()
    dpg.set_value(tag, path)


def main():
    dpg.create_context()

    with dpg.font_registry():
        default_font = dpg.add_font("RedHatText-Medium.ttf", 18)

    with dpg.window(tag="Primary Window"):
        dpg.add_text(f"{config.NAME} v{config.VERSION}")

        # Input path
        dpg.add_text("Input path (*)")
        with dpg.group(horizontal=True):
            input_path = dpg.add_input_text(tag="input_path", hint="Path to las files")
            dpg.add_button(
                label="Browse", callback=lambda _: browse_files("input_path")
            )

        # Output path
        dpg.add_text("Output path (*)")
        with dpg.group(horizontal=True):
            output_path = dpg.add_input_text(tag="output_path", hint="Output directory")
            dpg.add_button(
                label="Browse", callback=lambda _: browse_files("output_path")
            )

        dpg.add_text(
            "Classes to be left in each file (Insert class id's separated by comma):",
            wrap=300,
        )
        dpg.add_input_text(tag="classes", hint="Classes to be left in each file")

        dpg.add_text(
            "Classes to skip (Insert class id's separated by comma):", wrap=300
        )
        dpg.add_input_text(tag="classes_to_skip", hint="Classes to skip")

        dpg.add_progress_bar(tag="progress_bar", width=500, height=20)
        dpg.hide_item("progress_bar")

        dpg.add_button(
            label="Run",
            tag="Run",
            callback=lambda _: run(
                dpg.get_value(input_path),
                dpg.get_value(output_path),
                dpg.get_value("classes"),
                dpg.get_value("classes_to_skip"),
            ),
        )

        dpg.bind_font(default_font)

    dpg.create_viewport(title="Classification splitter", width=600, height=400)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    dpg.start_dearpygui()
    dpg.destroy_context()
    dpg.create_context()


if __name__ == "__main__":
    main()

import { Model } from "./model";

export function filesSelectController(model: Model, file: any, redraw: any) {
    model.addFiles(file);
    redraw();
}
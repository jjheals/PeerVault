import React from "react";

export class Model {
    filesToUpload: File[];
    filesUploaded: File[];


    constructor() {
        this.filesToUpload = [];
        this.filesUploaded = [];
    }

    addFiles(files: any) {
        for (const file of files) {
            let newFile = new File(file);
            this.filesToUpload.push(newFile);
            console.log("Added new file:\n" + newFile.printFileStats());
        }
    }

    getFilesToUpload(): File[] {
        return this.filesToUpload;
    }

    getTotalStorage(): number {
        let storage = 0;
        for (const file of this.filesToUpload) {
            storage += file.size;
        }
        return storage;
    }
} 

export class File {
    name: string;
    size: number; // file size in bytes
    lastModified: Date;
    uploadTime: Date;
    file: Object;

    constructor(file: any) {
        this.name = file.name;
        this.size = file.size;
        this.lastModified = new Date(file.lastModified);
        this.uploadTime = new Date(Date.now());
        this.file = file;
    }

    printFileStats(): string {
        return ("File name: " + this.name + "\n" +
                "File size: " + this.size + "\n" +
                "File date: " + this.lastModified.toLocaleString() + "\n" +
                "Upload date: " + this.uploadTime
        )
    }
}
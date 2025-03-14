export class Model {
    user: User;
    filesToUpload: File[];
    filesUploaded: File[];

    constructor() {
        this.user = new User(-1, "123.345.789", "dan", "dc:29", 32);
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

    removeFile(index: number) {
        this.filesToUpload.splice(index, 1);
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

export class User {
    pub_key: string;
    common_name: string;
    mac: string;
    ip: string;

    // allowed_to_receive: number;
    // total_storage_allocated: number;

    constructor(pub_key: string, common_name: string, mac: string, ip: string) 
    {
        this.pub_key = pub_key;
        this.common_name = common_name;
        this.mac = mac;
        this.ip = ip;
    }
}

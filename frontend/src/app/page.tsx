'use client';

import React from "react";
import { Model } from "@/model";
import { filesSelectController } from "@/controllers";

export default function Home() {
    const [model, setModel] = React.useState(new Model())
    const [redraw, forceRedraw] = React.useState(0);
    const [files, setFiles] = React.useState(undefined);

    function refresh() {
        forceRedraw(redraw + 1);
    }

    React.useEffect(() => {
      if (!files) {
        retreiveFilesToUpload(setFiles);
        console.log("files:", files);
      }
    }, [redraw]);

    function handleFilesSelect(event: any) {
        filesSelectController(model, event.target.files, refresh);
    }

    function FilesList(props) {
      if(!props.files) return;

      return (
        <div>
          <label>Total Storage needed for files: {model.getTotalStorage().toString()}</label>
          {props.files.map((file, index) => (
            <p key={index}>
              <label>{file.name} - {file.size} - {file.lastModified.toLocaleString()}</label>
            </p>
          ))}
        </div>
      )
    }

    function retreiveFilesToUpload(setFiles: any) {
      setFiles(model.getFilesToUpload());
    }

    return (
      <div className="itemCard">
        <div className="itemCardLeftContent">
          <div className="itemCardTitleText">Select Files to Share</div>
          <p>
            <input type="file" multiple onChange={handleFilesSelect}/>
          </p>
          <div>
            <FilesList files={files}/>
          </div>
        </div> 
      </div>
    )

}
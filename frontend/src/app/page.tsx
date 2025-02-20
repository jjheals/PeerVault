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
          <label>Total Size of Files: {model.getTotalStorage().toString()}</label>
          {props.files.map((file, index) => (
            <p key={index}>
              <label>{file.name} - {file.size}B</label>
            </p>
          ))}
        </div>
      )
    }

    function retreiveFilesToUpload(setFiles: any) {
      setFiles(model.getFilesToUpload());
    }

    return (
      <div className="header">
        <div className="header-row">
          <div className="titleText">PeerVault</div>
          <div className="header-options-row">
            <button>
              <div className="header-button-text-option-one">Sign In</div>
            </button>
            <button >
              <div className="header-button-text-option-two">Create Account</div>
            </button>
          </div>
        </div>
        <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
        <div className="ItemContainer">
          <div className="itemContainerContent">
            <div className="itemCard">
              <div className="itemCardLeftContent">
                <div className="itemCardTitleText">Select a Person to Share With</div>
              </div> 
            </div>
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
            <div className="itemCard">
              <div className="itemCardLeftContent">
                <div className="itemCardTitleText">Storage Type</div>
                <form>
                  <div>
                    <button>Share</button>
                  </div>
                  <div>
                    <button>Store</button>
                  </div>
                </form>
              </div>
            </div> 
            <button className="itemCard">Upload</button>
          </div>
        </div>
      </div>
    )

}
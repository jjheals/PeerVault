'use client'; //needed to handle site events (clicks / events / interactions)

import React from "react";
import Image from "next/image";
import { Model } from "@/model";
import { filesSelectController } from "@/controllers";
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { send } from "process";
import router from "next/router";
import { motion } from "framer-motion";

const PORT = 8000;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});


export default function Home() {
    const [model, setModel] = React.useState(new Model());
    const [redraw, forceRedraw] = React.useState(0);
    const [files, setFiles] = React.useState<any[]>([]);
    const [recipient, setRecipient] = React.useState("");
    const [users, setUsers] = React.useState<any[]>([]);
    const [identity, setIdentity] = React.useState();
    const [verifiedUser, setVerifiedUser] = React.useState(false)
    const [sendType, setSendType] = React.useState("");
    const [formValid, setFormValid] = React.useState(false);
    const [showStartSharing, setShowStartSharing] = React.useState(true);
    const [showSelectRecipient, setShowSelectRecipient] = React.useState(false);
    const [showFileSelect, setShowFileSelect] = React.useState(false);
    const [showStorageType, setShowStorageType] = React.useState(false);
    const [showConfirmation, setShowConfirmation] = React.useState(false);

    const router = useRouter();


    function refresh() {
        forceRedraw(redraw + 1);
    }

    React.useEffect(() =>{
      instance
      .get("/ui/get-peer-list'")
      .then(function (response){
        setUsers(response["data"]);
      })
      .catch (function (error) {
        console.log("errored:", error)
      });
    }, [redraw]);



    // Get the identity of the User on this device...
    React.useEffect(() =>{
      instance
      .get("/ui/whoami")
      .then(function (response){
        console.log("me: ", response["data"]["common-name"]);
        setIdentity(response["data"]["common-name"]);
        if (response["data"]["common-name"] != "Guest") {
          setVerifiedUser(true);
        }
      })
      .catch (function (error) {
        console.log("errored:", error)
      });
    }, [redraw]);


    // store the uploaded files
    React.useEffect(() => {
      retreiveFilesToUpload(setFiles);
      console.log("files:", files);
    }, [redraw]);


    // check if th upload functionality should be enabled
    React.useEffect(() => {
        CheckFormValid();
    }, [recipient, sendType, files]);


    // allow the user to REMOVE a file that has been selected from the list
    // TODO -- implementation does NOT work
    const removeFile = (removed:any) =>{
      console.log("button Clicked");

      var fileList = files;
      var fileToRemove = 0;

      removed = removed.name;

      for(let i = 0; i < fileList.length; i++){
        if (fileList[i].name == removed){
          fileToRemove = i;
        }
      }
      console.log("file to remove:", fileToRemove);

      fileList[fileToRemove] = fileList[fileList.length]
      setFiles(fileList)
    }


    // display the list of files selected to be shared or sent
    function FilesList(props: any) {
      if(!props.files) return;

      return (
        <div>
          <label>Total Size of Files: {model.getTotalStorage().toString()}</label>
          {props.files.map((file: any, index: any) => (
            <p key={index}>
              <label>{file.name} - {file.size}B </label>
              <button className= "redButton" onClick={() =>removeFile(file)} >X</button>
            </p>
          ))}
        </div>
      )
    }


    // stores the value for the files that have been selected
    function handleFilesSelect(event: any) {
      filesSelectController(model, event.target.files, refresh);
    }


    // get files & info from device 
    function retreiveFilesToUpload(setFiles: any) {
      setFiles(model.getFilesToUpload());
    }

    // stores the value for the recipient of the share
    const selectRecipient = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setRecipient(event.target.value);
      console.log(recipient);
    };

    // display the users that we are available to share/store with
    // TODO -- does NOT work... --> not interfaced with the new flask backend correctly... -->
    function DisplayUsers(props: any) {      
      if (!props.users) return <div>Loading</div>;
      console.log("props:", props.users);
      return (
        <select id="users" value={recipient} onChange={selectRecipient}>
          <option value="" disabled>Select an option</option>

          {props.users.map((users: any, index: any) => (
            <option key={index} value={users}>{users}</option>
          ))}
        </select>
      )
    }


    // stores the value for the type of file upload (share/store)
    const selectSendType = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setSendType(event.target.value);
    };


    // checks if there is data selected for recipient, files selected AND a send type
    function CheckFormValid() {
      if (sendType !== "" && recipient !== "" && files.length > 0) {
        setFormValid(true);
      } else {
        setFormValid(false);
      }
    };


    // send the request to store 
    // TODO --> not implemented...
    function uploadData() {  
      var toUser = recipient; 
      var files:any = files;
      var sendMethod = sendType;
         
      console.log("called upload");

      instance
      .post("/uploadData",
        {
          recipient: toUser,
          data: files,
          sendMethod: sendMethod
        }
      )
      .then(function (response){
        console.log("success");
      })
      .catch (function (error) {
        console.log("errored")
      });

      //remove all of the data??
      setRecipient("")
      setFiles([])
      setSendType("")
    }

    return (
      <div>
      <div className="header">
        <div className="header-row">
          <div className="titleText">PeerVault</div>

          {verifiedUser && (
            <div className = "header-options-row">
              <div className="subtitleText">Welcome, {identity}!</div>
              
              <a href={`/accountInfo/${identity}`} className="header-button-text-option-two">
                Account Info
              </a>
              <a className="header-button-text-option-two" onClick={() => router(`/accountInfo/${identity}`)}>
                Account Info 2
              </a>

            </div>

          )}

          {!verifiedUser && (            
            <div className="header-options-row">            
              <div className="subtitleText">Please Log In!</div>
              <button onClick={()=> router.push("/createAccount/")}>
                <div className="header-button-text-option-two">Create Account</div>
              </button>
            </div>
          )}
          {verifiedUser && (
            <div className="header-options-row">
              <div className="relative inline-block">
                <button onClick={() => router.push("/pendingRequests")}>
                  <div className="hover" title="Direct Requests">
                    <Image
                      className="dark"
                      src="/inbox-alt-1-svgrepo-com.svg"
                      alt="direct request icon"
                      width={50}
                      height={50}
                    />
                  </div>
                </button>
                <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white text-xs font-bold">
                  {30}
                </span>
              </div>
              <div className="icon-padding"></div>
              <div className="relative inline-block">
                <button onClick={() => router.push("/pendingRequests")}>
                  <div className="hover" title="Universal Requests">
                    <Image
                      className="dark"
                      src="/globe.svg"
                      alt="universal request icon"
                      width={50}
                      height={50}
                    />
                  </div>
                </button>
                <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white text-xs font-bold">
                  {30}
                </span>
              </div>
              <div className="icon-padding"></div>
              <button onClick={() => router.push("/accountSettings")}>
                <div className="hover" title="Account Settings">
                  <Image
                    className="dark"
                    src="/settings-2-svgrepo-com.svg"
                    alt="account settings icon"
                    width={50}
                    height={50}
                  />
                </div>
              </button>
              <div className="icon-padding"></div>
            </div>
          )}
        </div>
      <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
      </div>
        {showStartSharing && (
          <div>
            <div className="flex items-center justify-center">
              <motion.button
                className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg"
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                onClick={() => handleContinue(1)}
              >
                Start Sharing
              </motion.button>
            </div>
          </div>
        )}
        {verfifiedUser && showSelectRecipient && (
          <div>
            <div className="ItemContainer">
              <div className="itemContainerContent">
                <div className="itemCard">

                  <div className="itemCardLeftContent">
                    <div className="itemCardTitleText">Select a Person to Share With</div>
                    <div className="dropdown">
                      <button className="dropbtn">Possible Recipients</button>
                      <div className="dropdown-content">
                      <div>
                        <label htmlFor="users">Choose a user: </label>
                        <DisplayUsers users={users}/>
                      </div>
                      </div>
                    </div>
                    {recipient && <p>You selected: {recipient}</p>}
                  </div> 
                </div>
              </div>
            </div>
            <div className="flex items-center justify-center flex-col space-y-4">
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={() => handleContinue(2)}>
                  Continue
                </button>
              </div>
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        {verfifiedUser && showFileSelect && (
          <div>
            <div className="ItemContainer">
              <div className="itemContainerContent">
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
              </div>
            </div>
            <div className="flex items-center justify-center flex-col space-y-4">
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={() => handleContinue(3)}>
                  Continue
                </button>
              </div>
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        {verfifiedUser && showStorageType && (
          <div>
            <div className="ItemContainer">
              <div className="itemContainerContent">
                <div className="itemCard">
                  <div className="itemCardLeftContent">
                    <div className="itemCardTitleText">Storage Type</div>
                      <select id="sendType" value={sendType} onChange={selectSendType}>
                        <option value="" disabled>Select an type</option>
                        <option value="share">Share</option>
                        <option value="store">Store</option>
                      </select>
                      
                      {sendType && <p>You selected: {sendType}</p>}
                  </div>
                </div> 
              </div>
            </div>
            <div className="flex items-center justify-center flex-col space-y-4">
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={() => handleContinue(4)}>
                  Continue
                </button>
              </div>
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        {verfifiedUser && showConfirmation && (
          <div>
            <div className="ItemContainer">
              <div className="itemContainerContent">
                <div className="itemCard">
                  <div className="itemCardLeftContent">
                    <div className="itemCardTitleText">Storage Type</div>
                      <div>
                        <FilesList files={files}/>
                      </div>
                  </div>
                </div> 
              </div>
            </div>
            <div className="flex items-center justify-center flex-col space-y-4">
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={() => handleContinue(5)}>
                  Upload
                </button>
              </div>
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    )

  }
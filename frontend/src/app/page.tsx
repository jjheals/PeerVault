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
    const [files, setFiles] = React.useState([]);
    const [recipient, setRecipient] = React.useState("");
    const [users, setUsers] = React.useState(undefined);
    const [identity, setIdentity] = React.useState();
    const [verfifiedUser, setVerifiedUser] = React.useState(false)
    const [sendType, setSendType] = React.useState("");
    const [formValid, setFormValid] = React.useState(false);
    const [showStartSharing, setShowStartSharing] = React.useState(true);
    const [showSelectRecipient, setShowSelectRecipient] = React.useState(false);
    const [showFileSelect, setShowFileSelect] = React.useState(false);
    const [showStorageType, setShowStorageType] = React.useState(false);
    const [showConfirmation, setShowConfirmation] = React.useState(false);

    function refresh() {
        forceRedraw(redraw + 1);
    }

    React.useEffect(() =>{
      instance
      .get("/users")
      .then(function (response){
        // The response is the response of the get request
        console.log("ret: ", response.data.users);
        setUsers(response.data.users);
      })
      .catch (function (error) {
        console.log("errored:", error)
      });
    }, [redraw]);



    React.useEffect(() =>{
      instance
      .get("/ui/whoami")
      .then(function (response){
        console.log("me: ", response.data.identity);
        setIdentity(response.data.common_name);
        if (response.data.identity != "Guest") {
          setVerifiedUser(true);
        }
      })
      .catch (function (error) {
        console.log("errored:", error)
      });
    }, [redraw]);


    React.useEffect(() => {
      retreiveFilesToUpload(setFiles);
      console.log("files:", files);
    }, [redraw]);

    React.useEffect(() => {
        CheckFormValid();
    }, [recipient, sendType, files]);

    function FilesList(props: any) {
      if(!props.files) return;

      return (
        <div>
          <label>Total Size of Files: {model.getTotalStorage().toString()}</label>
          {props.files.map((file: any, index: any) => (
            <p key={index}>
              <label>{file.name} - {file.size}B</label>
            </p>
          ))}
        </div>
      )
    }

    function handleFilesSelect(event: any) {
      filesSelectController(model, event.target.files, refresh);
    }

    function retreiveFilesToUpload(setFiles: any) {
      setFiles(model.getFilesToUpload());
    }

    const selectRecipient = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setRecipient(event.target.value);
      console.log(recipient);
    };
    const router = useRouter();

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

    const selectSendType = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setSendType(event.target.value);
    };

    function CheckFormValid() {
      if (sendType !== "" && recipient !== "" && files.length > 0) {
        setFormValid(true);
      } else {
        setFormValid(false);
      }
    };

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

    const handleContinue = (value:number) => {
      if (value == 1) {
        setShowStartSharing(false);
        setShowSelectRecipient(true);
      }
      else if (value == 2) {
        setShowSelectRecipient(false);
        setShowFileSelect(true);
      }
      else if (value == 3) {
        setShowFileSelect(false);
        setShowStorageType(true);
      }
      else if (value == 4) {
        setShowStorageType(false);
        setShowConfirmation(true);
      }
      else if (value == 5) {
        uploadData();
        returnHome();
      }
      refresh();
    };

    function resetShow() {
      setShowSelectRecipient(false);
      setShowFileSelect(false);
      setShowStorageType(false);
      setShowConfirmation(false);
    }

    function handleCancel(event:any) {
      setShowStartSharing(true);
      resetShow();
      refresh();
    }

    function returnHome() {
      setShowStartSharing(true);
      resetShow();
      refresh();
    }

    return (
      <div>
      <div className="header">
        <div className="header-row">
          <div className="titleText">PeerVault</div>
          {!verfifiedUser && (
            <div className="header-options-row">
              <button onClick={()=> router.push("/createAccount/")}>
                <div className="header-button-text-option-two">Create Account</div>
              </button>
            </div>
          )}
          {verfifiedUser && (
            <div className="header-options-row">
              <div className="relative inline-block">
                <button onClick={() => router.push("/pendingRequests")}>
                  <div className="hover" title="Pending Sent Requests">
                    <Image
                      className="dark"
                      src="/send-svgrepo-com.svg"
                      alt="pending sent icon"
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
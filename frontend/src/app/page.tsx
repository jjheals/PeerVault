'use client';

import React from "react";
import { Model } from "@/model";
import { filesSelectController } from "@/controllers";
import { useRouter } from 'next/navigation';

export default function Home() {
    const [model, setModel] = React.useState(new Model())
    const [redraw, forceRedraw] = React.useState(0);
    const [files, setFiles] = React.useState(undefined);
    const [recipeint, setRecipient] = React.useState("");
    var availableUsers = []


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

    function FilesList(props: any) {
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

    function getUsers(): string[]{
      // try {
      //   const response = await fetch("http://localhost:5000/users", {
      //     method: "GET",
      //     headers: { "Content-Type": "application/json" }
      //   });
  
      //   const data = await response.json();
      //   alert(data.message);
      // } 
      // catch (error)
      // {
      //   console.error("Error:", error);
      //   alert("Failed to get users.");
      // }
      return ["dan", "justin", "lily", "quentin"]
    };

    // const getMe = async() =>{
    //   var data = "Lily"
    //   // try {
    //   //   const response = fetch("http://localhost:5000/whoAmI", {
    //   //     method: "GET",
    //   //     headers: { "Content-Type": "application/json" }
    //   //   });
  
    //   //   var resp = await response.json();
    //   //   alert(resp.message);
    //   // } 
    //   // catch (error)
    //   // {
    //   //   console.error("Error:", error);
    //   //   alert("Failed to get identity.");
    //   // }
    //   // data = resp.data;
    //   return data;
    // };

    const selectRecipient = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setRecipient(event.target.value);
    };
    const router = useRouter();

    // var username = getMe();
    var username = "Guest"

    availableUsers = getUsers();

    return (
      <div className="header">
        <div className="header-row">
          <div className="titleText">PeerVault</div>
          <div className="subtitleText">Welcome, {username}!</div>
          <div className="header-options-row">
            
            <button onClick={()=> router.push("/signIn/")}>
              <div className="header-button-text-option-one">Sign In</div>
            </button>

            <button onClick={()=> router.push("/createAccount/")}>
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
                <div className="dropdown">
                  <button className="dropbtn">Possible Recipients</button>
                  <div className="dropdown-content">
                  <div>
                    <label htmlFor="users">Choose a user: </label>
                    <select id="users" value={recipeint} onChange={selectRecipient}>
                      <option value="" disabled>Select an option</option>

                      {availableUsers.map((users, index) => (
                        <option key={index} value={users}>{users}</option>
                      ))}
                    </select>
                  </div>
                  </div>
                </div>
                {recipeint && <p>You selected: {recipeint}</p>}
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
                    <button className="littleButton">Share</button>
                  </div>
                  <div>
                    <button className="littleButton">Store</button>
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